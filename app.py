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
        products = df[product_col].dropna().unique()
        selected_products = st.sidebar.multiselect("Products", options=products, default=products[:20])
        customers = df[customer_col].dropna().unique()
        selected_customers = st.sidebar.multiselect("Customers", options=customers, default=customers[:50])

        df_filtered = df[(df[product_col].isin(selected_products)) & (df[customer_col].isin(selected_customers))].copy()
        df_curr = df_filtered[df_filtered['FY'] == fy_selector].copy()
        df_prev = df_filtered[df_filtered['FY'] == prev_fy].copy() if prev_fy else pd.DataFrame()

        if df_curr.empty:
            st.error("❌ No data for selected filters/FY")
            st.stop()

        st.sidebar.success(f"✅ Filtered: {len(df_filtered):,} rows")

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

    # FIXED Monthly Analysis
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

    st.markdown("### 📊 Monthly Breakdown")
    col1, col2, col3 = st.columns(3)
    col1.metric("📈 Total Growth", f"{safe_growth_calc(curr_total, prev_total):+.1f}%")
    col2.metric("🥇 Best Month", f"{monthly_comparison['YoY_Growth_%'].max():+.1f}%")
    col3.metric("📉 Worst Month", f"{monthly_comparison['YoY_Growth_%'].min():+.1f}%")

    st.dataframe(monthly_comparison[['Month', 'Current_FY', 'Previous_FY', 'YoY_Growth_%']].round(), column_config={"Month": st.column_config.TextColumn("Month"), "Current_FY": st.column_config.NumberColumn("Current", format="%.0f"), "Previous_FY": st.column_config.NumberColumn("Previous", format="%.0f"), "YoY_Growth_%": st.column_config.NumberColumn("YoY %", format="%.1f%%")}, height=280, width='stretch')

    st.markdown("### 🔥 Growth Heatmap")
    fig_heatmap = px.imshow(monthly_comparison.set_index('Month')[['Current_FY', 'Previous_FY', 'YoY_Growth_%']].T, labels=dict(color="Value"), color_continuous_scale="RdYlGn", title="Monthly Performance Matrix", aspect="auto")
    fig_heatmap.update_layout(height=350, margin=dict(l=50, r=50, t=50, b=50))
    st.plotly_chart(fig_heatmap, width='stretch')

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

    # Customer Analysis
    st.markdown("---")
    st.subheader("👥 Customer Analysis")
    all_customers = set(df_prev[customer_col].dropna()) | set(df_curr[customer_col].dropna())
    records = []
    for cust in sorted(all_customers):
        prev_sales = df_prev[df_prev[customer_col] == cust][qty_col].sum() if not df_prev.empty else 0
        curr_sales = df_curr[df_curr[customer_col] == cust][qty_col].sum()
        if prev_sales > 0 and curr_sales > 0:
            growth_pct = safe_growth_calc(curr_sales, prev_sales)
            status, growth_display = "🟢 Active", f"{growth_pct:+.1f}%"
        elif prev_sales > 0 and curr_sales == 0:
            status, growth_display = "🔴 Lost", "-100%"
        elif prev_sales == 0 and curr_sales > 0:
            status, growth_display = "🟢 New", "∞%"
        else:
            status, growth_display = "⚪ Inactive", "0%"
        records.append([cust, prev_sales, curr_sales, growth_display, status])
    
    behavior_df = pd.DataFrame(records, columns=["Customer", "Prev FY", "Curr FY", "Growth %", "Status"])
    st.dataframe(behavior_df.sort_values("Curr FY", ascending=False), width='stretch')

    # Downloads
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button(label="📥 Current FY", data=df_curr.to_csv(index=False), file_name=f"sales_{fy_selector.replace('-','_')}.csv", mime="text/csv")
    with col2:
        st.download_button(label="📊 Monthly Analysis", data=monthly_comparison.to_csv(index=False), file_name="monthly_analysis.csv", mime="text/csv")
    with col3:
        st.download_button(label="🔄 Full Data", data=df.to_csv(index=False), file_name="full_dataset.csv", mime="text/csv")

else:
    st.info("👆 **Upload CSV/Excel with: Date, Product, Customer, Quantity**")
    st.markdown("""
    ```
    Date        | Product | Customer | Quantity
    2023-04-15  | Wheat   | ABC Corp | 1000
    2023-05-20  | Rice    | XYZ Ltd  | 1500
    ```
    **Needs 2+ FY data (Apr-Mar)**  
    """)