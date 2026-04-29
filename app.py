import os
os.environ["STREAMLIT_DATAFRAME_SERIALIZATION"] = "legacy"
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

st.set_page_config(page_title="AI Sales Dashboard", layout="wide")
st.title("📊 AI-Powered Sales Analytics Dashboard")
st.markdown("---")

def find_column(df, names):
    for col in df.columns:
        for name in names:
            if name.lower() in col.lower():
                return col
    return None

@st.cache_data
def load_data(file):
    if file.name.endswith('.csv'):
        return pd.read_csv(file)
    else:
        return pd.read_excel(file)

def safe_growth_calc(curr, prev):
    if prev == 0:
        return float('inf') if curr > 0 else 0
    return ((curr - prev) / prev) * 100

# 🔥 FIXED LOST LOGIC + ENHANCED RECOVERED
def mark_lost_streaks(df, customer_col='Customer', product_col='Product'):
    """✅ FIXED: Only marks 3rd+ month as Lost, keeps earlier months as Inactive"""
    df = df.copy()
    
    for (cust, product), idx in df.groupby([customer_col, product_col]).groups.items():
        group = df.loc[idx].sort_values('Month_Order')
        
        inactive_streak = 0
        
        for i in group.index:
            if df.loc[i, 'Status'] == "🟡 Inactive":
                inactive_streak += 1
            else:
                inactive_streak = 0
            
            # ✅ FIXED: Only mark CURRENT month when streak >= 3
            if inactive_streak >= 3:
                df.loc[i, 'Status'] = "🔴 Lost"
    
    return df

def mark_recovered(df, customer_col='Customer', product_col='Product'):
    """🟣 PRO LEVEL: Detects meaningful recovery with context"""
    df = df.copy()
    
    for (cust, product), idx in df.groupby([customer_col, product_col]).groups.items():
        group = df.loc[idx].sort_values('Month_Order')
        was_lost = False
        
        for i in group.index:
            current_status = df.loc[i, 'Status']
            
            if current_status == "🔴 Lost":
                was_lost = True
            
            # 🔥 PRO LEVEL: Recovery with context
            elif was_lost and current_status in ["🟢 Active", "🔵 Expansion"]:
                recovery_context = "🟢 Active" if current_status == "🟢 Active" else "🔵 Expansion"
                df.loc[i, 'Status'] = f"🟣 Recovered ({recovery_context})"
                was_lost = False  # reset after recovery
    
    return df

uploaded_file = st.sidebar.file_uploader("Upload Sales Data", type=['csv','xlsx'])

if uploaded_file:
    with st.spinner("Loading and processing data..."):
        df = load_data(uploaded_file)
        date_col = find_column(df, ['date', 'Date', 'DATE'])
        product_col = find_column(df, ['product', 'Product', 'PRODUCT'])
        customer_col = find_column(df, ['customer', 'Customer', 'CUSTOMER', 'client'])
        qty_col = find_column(df, ['qty', 'quantity', 'Qty', 'Quantity', 'KG', 'kg'])

        missing_cols = []
        if not date_col: missing_cols.append("Date")
        if not product_col: missing_cols.append("Product") 
        if not customer_col: missing_cols.append("Customer")
        if not qty_col: missing_cols.append("Quantity")

        if missing_cols:
            st.error(f"❌ Required columns not found: {', '.join(missing_cols)}")
            st.info("📋 Expected: date/product/customer/qty/quantity/kg")
            st.stop()

        original_rows = len(df)
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        df = df.dropna(subset=[date_col])
        df[qty_col] = pd.to_numeric(df[qty_col], errors='coerce')
        df = df.dropna(subset=[qty_col])
        cleaned_rows = len(df)
        st.sidebar.info(f"✅ Cleaned: {original_rows:,} → {cleaned_rows:,} rows")

        df['Month'] = df[date_col].dt.strftime('%b')
        df['Month_Num'] = df[date_col].dt.month
        df['Year'] = df[date_col].dt.year
        df['FY'] = df[date_col].apply(lambda x: f"{x.year}-{x.year+1}" if x.month >= 4 else f"{x.year-1}-{x.year}")

        fy_list = sorted(df['FY'].unique())
        if len(fy_list) < 2:
            st.error("❌ Need 2+ financial years for comparison")
            st.stop()

        st.sidebar.subheader("📅 Financial Year")
        fy_selector = st.sidebar.selectbox("Select Current FY", fy_list, index=len(fy_list)-1)
        prev_fy = fy_list[fy_list.index(fy_selector)-1] if len(fy_list) > 1 else None
        st.sidebar.markdown("---")

        st.sidebar.header("🔍 Filters")
        products = sorted(df[product_col].dropna().unique())
        customers = sorted(df[customer_col].dropna().unique())
        
        st.sidebar.subheader("📦 Products")
        selected_products = st.sidebar.multiselect(
            "Select Products (All selected by default)", 
            options=products, 
            default=products
        )
        
        st.sidebar.subheader("👥 Customers")
        selected_customers = st.sidebar.multiselect(
            "Select Customers (All selected by default)", 
            options=customers, 
            default=customers
        )
        
        st.sidebar.markdown("---")
        use_date_filter = st.sidebar.checkbox("📅 Custom Date Range", value=False, help="Filter by specific date range (optional)")
        
        if use_date_filter:
            date_range = st.sidebar.date_input(
                "Select Date Range",
                value=(df[date_col].min().date(), df[date_col].max().date()),
                min_value=df[date_col].min().date(),
                max_value=df[date_col].max().date()
            )
            
            if len(date_range) == 2:
                start_date, end_date = date_range
            elif len(date_range) == 1:
                start_date = end_date = date_range[0]
            else:
                start_date, end_date = df[date_col].min().date(), df[date_col].max().date()
        else:
            start_date, end_date = df[date_col].min().date(), df[date_col].max().date()

        df_filtered = df[
            (df[product_col].isin(selected_products)) & 
            (df[customer_col].isin(selected_customers)) & 
            (df[date_col] >= pd.to_datetime(start_date)) &
            (df[date_col] <= pd.to_datetime(end_date))
        ].copy()
        
        df_curr = df_filtered[df_filtered['FY'] == fy_selector].copy()
        df_prev = df_filtered[df_filtered['FY'] == prev_fy].copy() if prev_fy else pd.DataFrame()

        if df_curr.empty:
            st.error("❌ No data for selected filters/FY")
            st.stop()

        st.sidebar.success(f"✅ **FULL DATA**: {len(df_filtered):,} rows | {len(selected_products):,} products | {len(selected_customers):,} customers")
        if len(selected_products) < len(products):
            st.sidebar.warning(f"🔍 **Filtered**: {len(products)-len(selected_products):,} products excluded")
        if len(selected_customers) < len(customers):
            st.sidebar.warning(f"🔍 **Filtered**: {len(customers)-len(selected_customers):,} customers excluded")
        if use_date_filter:
            date_range_display = f"{start_date.strftime('%b %Y')} - {end_date.strftime('%b %Y')}"
            st.sidebar.info(f"📅 **Date Range**: {date_range_display}")

    # KPIs
    st.markdown("## 📊 Key Performance Indicators")
    col1, col2, col3, col4 = st.columns(4)
    curr_total = df_curr[qty_col].sum()
    prev_total = df_prev[qty_col].sum() if not df_prev.empty else 0
    growth = safe_growth_calc(curr_total, prev_total)
    col1.metric("Current FY Total", f"{curr_total:,.0f}", f"{growth:+.1f}%" if prev_total > 0 else "New")
    col2.metric("Active Customers", df_curr[customer_col].nunique())
    col3.metric("Products Sold", df_curr[product_col].nunique())
    col4.metric("Data Points", len(df_curr))

    # Top Products & Customers
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📦 Top Products")
        top_products = df_curr.groupby(product_col)[qty_col].sum().sort_values(ascending=False).head(10).reset_index()
        fig1 = px.bar(top_products, x=qty_col, y=product_col, orientation='h', title=f"Total: {curr_total:,.0f}", color=qty_col, color_continuous_scale="Viridis")
        fig1.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig1, width='stretch')

    with col2:
        st.subheader("👥 Top Customers")
        top_customers = df_curr.groupby(customer_col)[qty_col].sum().sort_values(ascending=False).head(10).reset_index()
        fig2 = px.bar(top_customers, x=qty_col, y=customer_col, orientation='h', title="Top Customers", color=qty_col, color_continuous_scale="Plasma")
        fig2.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig2, width='stretch')

    # Monthly Analysis
    st.markdown("---")
    st.subheader("📈 Monthly Performance Comparison (YoY)")

    month_order = ['Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec','Jan','Feb','Mar']
    month_num_map = {'Apr':4, 'May':5, 'Jun':6, 'Jul':7, 'Aug':8, 'Sep':9, 'Oct':10, 'Nov':11, 'Dec':12, 'Jan':1, 'Feb':2, 'Mar':3}
    
    curr_monthly = df_curr.groupby(['FY', 'Month_Num'])[qty_col].sum().reset_index()
    prev_monthly = df_prev.groupby(['FY', 'Month_Num'])[qty_col].sum().reset_index() if not df_prev.empty else pd.DataFrame()
    
    monthly_comparison = pd.DataFrame({'Month': month_order, 'Month_Num': [month_num_map[m] for m in month_order]})
    
    curr_monthly_filtered = curr_monthly[curr_monthly['FY'] == fy_selector]
    monthly_comparison = monthly_comparison.merge(curr_monthly_filtered.rename(columns={qty_col: 'Current_FY'}), on='Month_Num', how='left')

    if not prev_monthly.empty and prev_fy:
        prev_monthly_filtered = prev_monthly[prev_monthly['FY'] == prev_fy]
        monthly_comparison = monthly_comparison.merge(prev_monthly_filtered.rename(columns={qty_col: 'Previous_FY'}), on='Month_Num', how='left')
    else:
        monthly_comparison['Previous_FY'] = 0

    monthly_comparison = monthly_comparison.fillna(0)
    monthly_comparison['Qty_Diff'] = monthly_comparison['Current_FY'] - monthly_comparison['Previous_FY']
    monthly_comparison['YoY_Growth_%'] = monthly_comparison.apply(lambda row: safe_growth_calc(row['Current_FY'], row['Previous_FY']), axis=1)

    calculated_total = monthly_comparison['Current_FY'].sum()
    st.success(f"✅ Monthly Sum: {calculated_total:,.0f} = Yearly Total: {curr_total:,.0f} ✓")

    # Monthly Chart
    fig_monthly = go.Figure()
    fig_monthly.add_trace(go.Scatter(x=monthly_comparison['Month'], y=monthly_comparison['Current_FY'], mode='lines+markers+text', name=f'{fy_selector}', line=dict(color='#10B981', width=5), marker=dict(size=12), text=[f"{int(x):,}" for x in monthly_comparison['Current_FY']], textposition="top center", textfont=dict(size=11, color="#059669")))
    
    if not df_prev.empty and prev_fy:
        fig_monthly.add_trace(go.Scatter(x=monthly_comparison['Month'], y=monthly_comparison['Previous_FY'], mode='lines+markers', name=f'{prev_fy}', line=dict(color='#EF4444', width=3, dash='dash'), marker=dict(size=9)))

    for i, row in monthly_comparison.iterrows():
        if row['Previous_FY'] > 0 and abs(row['YoY_Growth_%']) > 15:
            color = "#1E40AF" if row['YoY_Growth_%'] > 0 else "#DC2626"
            fig_monthly.add_annotation(x=row['Month'], y=row['Current_FY']*1.05, text=f"{row['YoY_Growth_%']:+.0f}%", showarrow=True, arrowhead=2, font=dict(size=10, color=color))

    fig_monthly.update_layout(title=f"📈 Monthly Trend | Total: {calculated_total:,.0f}", xaxis_title="Month", yaxis_title="Quantity", height=500, showlegend=True, template='plotly_white', hovermode='x unified')
    st.plotly_chart(fig_monthly, width='stretch')

    # Monthly Breakdown & Dataframe
    st.markdown("### 📊 Monthly Breakdown")
    col1, col2, col3 = st.columns(3)
    total_qty_diff = monthly_comparison['Qty_Diff'].sum()
    col1.metric("📈 Total Qty Change", f"{total_qty_diff:+,.0f}", f"{safe_growth_calc(curr_total, prev_total):+.1f}%")
    col2.metric("🥇 Best Month", f"{monthly_comparison['Qty_Diff'].max():+.0f}")
    col3.metric("📉 Worst Month", f"{monthly_comparison['Qty_Diff'].min():+.0f}")

    st.dataframe(
        monthly_comparison[['Month', 'Current_FY', 'Previous_FY', 'Qty_Diff', 'YoY_Growth_%']].round(),
        column_config={
            "Month": st.column_config.TextColumn("Month"),
            "Current_FY": st.column_config.NumberColumn("Current FY", format="%.0f"),
            "Previous_FY": st.column_config.NumberColumn("Previous FY", format="%.0f"),
            "Qty_Diff": st.column_config.NumberColumn("Qty Change\n(Current-Prev)", format="%.0f"),
            "YoY_Growth_%": st.column_config.NumberColumn("YoY %", format="%.1f%%")
        },
        height=280, 
        width='stretch'
    )

    # Heatmap
    st.markdown("### 🔥 Quantity Change Heatmap")
    heatmap_data = monthly_comparison.set_index('Month')[['Current_FY', 'Previous_FY', 'Qty_Diff']].round(0)
    fig_heatmap = px.imshow(
        heatmap_data.T, 
        labels=dict(color="Quantity"), 
        color_continuous_scale="RdYlGn", 
        title="📊 Monthly Quantity Changes (Current - Previous)",
        aspect="auto"
    )
    fig_heatmap.update_layout(height=400)
    st.plotly_chart(fig_heatmap, width='stretch')

    # =========================================================
    # 🧠 CUSTOMER-PRODUCT MONTHLY STATUS (ENHANCED WITH RECOVERED)
    # =========================================================
    st.markdown("---")
    st.subheader("🧠 Customer-Product Monthly Status (Advanced)")

    # Use already filtered data
    df_curr_cp = df_filtered[df_filtered['FY'] == fy_selector].copy()
    df_prev_cp = df_filtered[df_filtered['FY'] == prev_fy].copy() if prev_fy else pd.DataFrame()

    # 🔥 OPTIMIZATION 1: Pre-aggregated data (PERFORMANCE FIX)
    curr_agg = df_curr_cp.groupby([customer_col, product_col, 'Month_Num'])[qty_col].sum().reset_index(name='Curr_Qty')
    prev_agg = df_prev_cp.groupby([customer_col, product_col, 'Month_Num'])[qty_col].sum().reset_index(name='Prev_Qty') if not df_prev_cp.empty else pd.DataFrame()

    # 🔥 OPTIMIZATION 2: Get ALL combinations efficiently
    group_cols = [customer_col, product_col, 'Month_Num']
    all_combinations = pd.concat([
        curr_agg[group_cols],
        prev_agg[group_cols]
    ]).drop_duplicates().reset_index(drop=True)

    # 🔥 OPTIMIZATION 3: Vectorized merge (NO LOOPS!)
    comparison_df = all_combinations.merge(curr_agg[['Curr_Qty', customer_col, product_col, 'Month_Num']], on=group_cols, how='left')
    comparison_df = comparison_df.merge(prev_agg[['Prev_Qty', customer_col, product_col, 'Month_Num']], on=group_cols, how='left')
    comparison_df['Curr_Qty'] = comparison_df['Curr_Qty'].fillna(0)
    comparison_df['Prev_Qty'] = comparison_df['Prev_Qty'].fillna(0)

    # Previous customers set for reference
    prev_customers_set = set(df_prev_cp[customer_col].unique()) if not df_prev_cp.empty else set()

    # 🎯 ENHANCED STATUS LOGIC (CLEARER NAMES)
    def assign_status(row):
        if row['Prev_Qty'] > 0 and row['Curr_Qty'] > 0:
            return "🟢 Active"
        elif row['Prev_Qty'] > 0 and row['Curr_Qty'] == 0:
            return "🟡 Inactive"
        elif row['Prev_Qty'] == 0 and row['Curr_Qty'] > 0:
            if row[customer_col] in prev_customers_set:
                return "🔵 Expansion"  # Existing customer, new product
            else:
                return "🟡 New Customer"
        else:
            return "⚪ No Activity"

    comparison_df['Status'] = comparison_df.apply(assign_status, axis=1)

    # 🔥 OPTIMIZATION 4: Proper FY month ordering
    fy_order_map = {m:i for i,m in enumerate([4,5,6,7,8,9,10,11,12,1,2,3])}
    comparison_df['Month_Order'] = comparison_df['Month_Num'].map(fy_order_map)
    comparison_df = comparison_df.sort_values(['Customer', 'Product', 'Month_Order']).reset_index(drop=True)
    
    # Rename columns EARLY for function compatibility
    comparison_df = comparison_df.rename(columns={customer_col: 'Customer', product_col: 'Product'})

    # ✅ FIXED LOST LOGIC (Safe index handling)
    comparison_df = mark_lost_streaks(comparison_df)
    
    # 🟣 ENHANCED RECOVERED LOGIC (After Lost marking)
    comparison_df = mark_recovered(comparison_df)

    # Convert Month Number to Name
    month_map = {
        4:'Apr',5:'May',6:'Jun',7:'Jul',8:'Aug',9:'Sep',
        10:'Oct',11:'Nov',12:'Dec',1:'Jan',2:'Feb',3:'Mar'
    }
    comparison_df['Month'] = comparison_df['Month_Num'].map(month_map)

    # 🚨 FIXED KPI INSIGHTS (Manager-level metrics - UNIQUE customer-product pairs)
    total_cp_combinations = len(comparison_df)
    lost_df = comparison_df[comparison_df['Status'] == "🔴 Lost"].drop_duplicates(subset=['Customer','Product'])
    lost_count = lost_df.shape[0]
    
    recovered_df = comparison_df[comparison_df['Status'].str.contains("Recovered")].drop_duplicates(subset=['Customer','Product'])
    recovered_count = recovered_df.shape[0]
    
    active_count = len(comparison_df[comparison_df['Status'] == "🟢 Active"])
    prev_cp_count = len(prev_agg)
    retention_rate = (active_count / prev_cp_count * 100) if prev_cp_count > 0 else 0
    expansion_count = len(comparison_df[comparison_df['Status'] == "🔵 Expansion"])

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("🔴 High Risk (Lost)", lost_count)
    col2.metric("🟢 Active", active_count)
    col3.metric("🟣 Recovered", recovered_count)
    col4.metric("💹 Retention Rate", f"{retention_rate:.1f}%")
    col5.metric("🔵 Expansion", expansion_count)

    # 🔥 RECOVERY INSIGHT
    if recovered_count > 0:
        st.info(f"🟣 **{recovered_count} customer-product pairs reactivated** after being Lost! 🎉")

    # 🔥 NEW FILTERS & SEARCH FOR Customer-Product Table
    st.markdown("### 🔍 Advanced Filters")
    filter_row1, filter_row2 = st.columns([2, 3])
    
    with filter_row1:
        # Search bar for Company name
        search_company = st.text_input("🔎 Search Company", placeholder="Type company name...")
    
    with filter_row2:
        # Dropdown filters (UPDATED with Recovered)
        all_statuses = sorted(comparison_df['Status'].unique())
        all_months = sorted(comparison_df['Month'].unique())
        all_products = sorted(comparison_df['Product'].dropna().unique())
        
        selected_status = st.multiselect("Status", options=all_statuses, default=all_statuses, key="cp_status")
        selected_months = st.multiselect("Months", options=all_months, default=all_months, key="cp_months")
        selected_products_cp = st.multiselect("Products", options=all_products[:20], default=all_products[:20], key="cp_products")

    # Apply filters
    filtered_cp_df = comparison_df.copy()
    
    if search_company:
        filtered_cp_df = filtered_cp_df[filtered_cp_df['Customer'].str.contains(search_company, case=False, na=False)]
    
    filtered_cp_df = filtered_cp_df[
        filtered_cp_df['Status'].isin(selected_status) &
        filtered_cp_df['Month'].isin(selected_months) &
        filtered_cp_df['Product'].isin(selected_products_cp)
    ]

    # FINAL DISPLAY with filter info
    st.info(f"📊 **Showing {len(filtered_cp_df):,} of {len(comparison_df):,} records")
    
    display_df = filtered_cp_df.sort_values(['Customer', 'Product', 'Month_Order']).drop(columns=['Month_Order'])
    st.dataframe(
        display_df[['Customer', 'Product', 'Month', 'Prev_Qty', 'Curr_Qty', 'Status']],
        height=500,
        width='stretch',
        column_config={
            "Status": st.column_config.TextColumn("Status", width="150px"),
            "Prev_Qty": st.column_config.NumberColumn("Prev Qty", format="%.0f"),
            "Curr_Qty": st.column_config.NumberColumn("Curr Qty", format="%.0f"),
            "Month": st.column_config.TextColumn("Month", width="80px")
        }
    )

    # Smart Insights
    st.markdown("---")
    st.subheader("🧠 Smart Insights")
    col1, col2, col3 = st.columns(3)
    top_product = df_curr.groupby(product_col)[qty_col].sum().idxmax()
    col1.success(f"🥇 **Top Product**: {top_product}")
    top_customer = df_curr.groupby(customer_col)[qty_col].sum().idxmax()
    col2.success(f"👑 **Top Customer**: {top_customer}")
    peak_month = monthly_comparison.loc[monthly_comparison['Current_FY'].idxmax(), 'Month']
    col3.info(f"📅 **Peak Month**: {peak_month}")

    # =========================================================
    # 👥 CUSTOMER ANALYSIS (ENHANCED WITH FILTERS & NEW COLUMN)
    # =========================================================
    st.markdown("---")
    st.subheader("👥 Customer Analysis")

    all_customers = set(df_prev[customer_col].dropna()) | set(df_curr[customer_col].dropna())

    records = []
    for cust in sorted(all_customers):
        prev_yearly_sales = df_prev[df_prev[customer_col] == cust][qty_col].sum() if not df_prev.empty else 0
        curr_yearly_sales = df_curr[df_curr[customer_col] == cust][qty_col].sum()
        
        # 🔥 NEW COLUMN: Previous FY Actual Month (highest month in prev FY)
        if not df_prev.empty and len(df_prev[df_prev[customer_col] == cust]) > 0:
            prev_monthly = df_prev[(df_prev[customer_col] == cust)].groupby('Month_Num')[qty_col].sum()
            prev_peak_month_num = prev_monthly.idxmax() if not prev_monthly.empty else None
            prev_peak_month = month_map.get(prev_peak_month_num, 'None')
            prev_peak_qty = prev_monthly.max()
        else:
            prev_peak_month = 'None'
            prev_peak_qty = 0
        
        prev_apr_sales = df_prev[(df_prev[customer_col] == cust) & (df_prev['Month_Num'] == 4)][qty_col].sum()
        curr_apr_sales = df_curr[(df_curr[customer_col] == cust) & (df_curr['Month_Num'] == 4)][qty_col].sum()
        apr_qty_diff = curr_apr_sales - prev_apr_sales
        
        if prev_yearly_sales > 0 and curr_yearly_sales > 0:
            yearly_growth = safe_growth_calc(curr_yearly_sales, prev_yearly_sales)
            if curr_apr_sales > 0 and prev_apr_sales > 0:
                status = f"🟢 Active (APR)"
                apr_status = f"{apr_qty_diff:+,.0f}"
            elif curr_apr_sales > 0:
                status = f"🟢 New APR"
                apr_status = f"+{curr_apr_sales:,.0f}"
            else:
                status = "🟡 Active"
                apr_status = "No APR"
            growth_display = f"{yearly_growth:+.1f}%"
        elif prev_yearly_sales > 0 and curr_yearly_sales == 0:
            status = "🔴 Lost"
            apr_status = f"-{prev_apr_sales:,.0f}"
            growth_display = "-100%"
        elif prev_yearly_sales == 0 and curr_yearly_sales > 0:
            status = "🟡 New"
            apr_status = f"+{curr_apr_sales:,.0f}"
            growth_display = "∞%"
        else:
            status = "⚪ Inactive"
            apr_status = "0"
            growth_display = "0%"
        
        records.append([cust, f"{prev_yearly_sales:,.0f}", f"{curr_yearly_sales:,.0f}", growth_display, 
                       status, apr_status, f"{prev_peak_month} ({prev_peak_qty:,.0f})"])

    behavior_df = pd.DataFrame(records, columns=["Customer", "Prev FY", "Curr FY", "Growth %", "Status", "APR Change", "Prev Peak Month"])
    
    # 🔥 NEW FILTERS & SEARCH FOR Customer Analysis Table
    st.markdown("### 🔍 Customer Filters")
    cust_filter_row1, cust_filter_row2 = st.columns([2, 2])
    
    with cust_filter_row1:
        search_customer = st.text_input("🔎 Search Customer", placeholder="Type customer name...", key="cust_search")
    
    with cust_filter_row2:
        all_customer_statuses = sorted(behavior_df['Status'].unique())
        selected_customer_status = st.multiselect("Status", options=all_customer_statuses, default=all_customer_statuses, key="cust_status")

    # Apply customer filters
    filtered_behavior_df = behavior_df.copy()
    
    if search_customer:
        filtered_behavior_df = filtered_behavior_df[filtered_behavior_df['Customer'].str.contains(search_customer, case=False, na=False)]
    
    filtered_behavior_df = filtered_behavior_df[filtered_behavior_df['Status'].isin(selected_customer_status)]

    st.info(f"👥 **Showing {len(filtered_behavior_df):,} of {len(behavior_df):,} customers")
    
    st.dataframe(
        filtered_behavior_df.sort_values("Curr FY", ascending=False),
        column_config={
            "Customer": st.column_config.TextColumn("Customer"),
            "Prev FY": st.column_config.NumberColumn("Prev FY Total", format="%.0f"),
            "Curr FY": st.column_config.NumberColumn("Curr FY Total", format="%.0f"),
            "Growth %": st.column_config.TextColumn("Growth %"),
            "Status": st.column_config.TextColumn("Status", width="150px"),
            "APR Change": st.column_config.TextColumn("APR Qty Change"),
            "Prev Peak Month": st.column_config.TextColumn("Prev FY Peak Month", width="180px")
        },
        height=400, 
        width='stretch'
    )

    # Customer Status Summary
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    active_apr = len(behavior_df[behavior_df['Status'].str.contains('APR|New APR', na=False)])
    total_customers = len(behavior_df)
    lost_customers = len(behavior_df[behavior_df['Status'].str.contains('Lost', na=False)])
    new_customers = len(behavior_df[behavior_df['Status'].str.contains('New', na=False)])

    col1.metric("🟢 Active APR", active_apr)
    col2.metric("🔴 Lost", lost_customers)
    col3.metric("🟡 New", new_customers)
    col4.metric("📊 Total", total_customers)

    # Downloads
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.download_button(label="📥 Current FY", data=df_curr.to_csv(index=False), file_name=f"sales_{fy_selector.replace('-','_')}.csv", mime="text/csv")
    with col2:
        st.download_button(label="📊 Monthly Analysis", data=monthly_comparison.to_csv(index=False), file_name="monthly_analysis.csv", mime="text/csv")
    with col3:
        st.download_button(label="🔄 Full Data", data=df.to_csv(index=False), file_name="full_dataset.csv", mime="text/csv")
    with col4:
        st.download_button(label="🧠 Customer-Product Status", data=display_df.to_csv(index=False), file_name="customer_product_status.csv", mime="text/csv")

else:
    st.info("👈 **Upload CSV/Excel with: Date, Product, Customer, Quantity**")
    st.markdown("""
    ```
    Date        | Product | Customer | Quantity
    2025-04-15  | ABC | HCL | 10000
    2025-05-20  | XYZ | HYPO| 250000
    ```
    **✅ Works with any column names containing: date/Date, product/Product, customer/Customer, qty/quantity/KG**
    """)