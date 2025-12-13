import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
sys.path.append("..")
from utils.api_client import api_client

st.set_page_config(
    page_title="Dashboard - Smart Gate Security",
    page_icon="🏠",
    layout="wide"
)

st.title("🏠 Security Command Dashboard")
st.markdown("Real-time overview of security operations")

# Auto-refresh option
col_refresh, col_time = st.columns([1, 3])
with col_refresh:
    if st.button("🔄 Refresh Data"):
        st.rerun()
with col_time:
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

st.markdown("---")

# Try to fetch data from API, use mock data if unavailable
try:
    dashboard_data = api_client.get_full_dashboard()
    stats = dashboard_data.get("stats", {})
    recent = dashboard_data.get("recent_activity", {})
    api_available = True
except:
    api_available = False
    # Mock data for demo
    stats = {
        "total_visitors_today": 45,
        "pending_approvals": 3,
        "active_visitors": 12,
        "total_entries_today": 128,
        "denied_entries_today": 5,
        "active_watchlist_alerts": 1,
        "open_incidents": 4,
        "critical_incidents": 1
    }
    recent = {
        "recent_entries": [],
        "recent_incidents": [],
        "active_alerts": []
    }

if not api_available:
    st.warning("⚠️ API not available. Showing demo data.")

# Key Metrics Row
st.markdown("### 📊 Key Metrics")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="Visitors Today",
        value=stats.get("total_visitors_today", 0),
        delta=f"{stats.get('active_visitors', 0)} active"
    )

with col2:
    st.metric(
        label="Gate Entries Today",
        value=stats.get("total_entries_today", 0),
        delta=f"-{stats.get('denied_entries_today', 0)} denied",
        delta_color="inverse"
    )

with col3:
    alerts = stats.get("active_watchlist_alerts", 0)
    st.metric(
        label="Active Alerts",
        value=alerts,
        delta="⚠️ Needs attention" if alerts > 0 else "✅ Clear"
    )

with col4:
    incidents = stats.get("open_incidents", 0)
    critical = stats.get("critical_incidents", 0)
    st.metric(
        label="Open Incidents",
        value=incidents,
        delta=f"{critical} critical" if critical > 0 else "No critical"
    )

st.markdown("---")

# Alert Section (if any active alerts)
if stats.get("active_watchlist_alerts", 0) > 0:
    st.markdown("### 🚨 Active Watchlist Alerts")
    
    alerts = recent.get("active_alerts", [])
    for alert in alerts:
        severity = alert.get("severity", "medium")
        if severity == "critical":
            st.error(f"""
            **CRITICAL ALERT** - {alert.get('watchlist_person_name', 'Unknown')}
            - Gate: {alert.get('gate_id', 'N/A')}
            - Confidence: {alert.get('confidence_score', 0):.1f}%
            - Time: {alert.get('created_at', 'N/A')}
            """)
        elif severity == "high":
            st.warning(f"""
            **HIGH ALERT** - {alert.get('watchlist_person_name', 'Unknown')}
            - Gate: {alert.get('gate_id', 'N/A')}
            - Confidence: {alert.get('confidence_score', 0):.1f}%
            """)
    
    if not alerts:
        st.info("Alert data loading...")
    
    st.markdown("---")

# Two column layout for charts and activity
left_col, right_col = st.columns([2, 1])

with left_col:
    st.markdown("### 📈 Entry Trends (Last 7 Days)")
    
    # Try to get trends from API
    try:
        trends_data = api_client.get_entry_trends(days=7)
        trends = trends_data.get("trends", [])
    except:
        # Mock trend data
        trends = [
            {"date": (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d"), 
             "allowed": 100 + i*5, "denied": 5 + i, "watchlist_alerts": i % 2}
            for i in range(6, -1, -1)
        ]
    
    if trends:
        df_trends = pd.DataFrame(trends)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_trends['date'],
            y=df_trends['allowed'],
            name='Allowed',
            fill='tozeroy',
            line=dict(color='#4CAF50')
        ))
        fig.add_trace(go.Scatter(
            x=df_trends['date'],
            y=df_trends['denied'],
            name='Denied',
            fill='tozeroy',
            line=dict(color='#f44336')
        ))
        
        fig.update_layout(
            height=300,
            margin=dict(l=0, r=0, t=30, b=0),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            xaxis_title="Date",
            yaxis_title="Entries"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No trend data available")

with right_col:
    st.markdown("### 📋 Incident Summary")
    
    # Try to get incident summary
    try:
        summary = api_client.get_incident_summary()
        by_severity = summary.get("by_severity", [])
    except:
        by_severity = [
            {"severity": "low", "count": 2},
            {"severity": "medium", "count": 3},
            {"severity": "high", "count": 1},
            {"severity": "critical", "count": 1}
        ]
    
    if by_severity:
        df_severity = pd.DataFrame(by_severity)
        
        colors = {
            'low': '#4CAF50',
            'medium': '#FFC107',
            'high': '#FF9800',
            'critical': '#f44336'
        }
        
        fig = px.pie(
            df_severity,
            values='count',
            names='severity',
            color='severity',
            color_discrete_map=colors,
            hole=0.4
        )
        fig.update_layout(
            height=250,
            margin=dict(l=0, r=0, t=0, b=0),
            showlegend=True,
            legend=dict(orientation="h")
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No open incidents")

st.markdown("---")

# Recent Activity Tables
st.markdown("### 📜 Recent Activity")

tab1, tab2, tab3 = st.tabs(["🚪 Gate Entries", "📋 Incidents", "👤 Visitors"])

with tab1:
    st.markdown("#### Recent Gate Entries")
    
    entries = recent.get("recent_entries", [])
    
    entry_data = []
    for entry in entries[:10]:
        status_emoji = {
            "allowed": "✅",
            "denied": "❌",
            "manual_verification": "⚠️",
            "watchlist_alert": "🚨"
        }
        entry_data.append({
            "Time": entry.get("timestamp", "N/A")[:19] if entry.get("timestamp") else "N/A",
            "Status": f"{status_emoji.get(entry.get('status', ''), '❓')} {entry.get('status', 'N/A')}",
            "Person": entry.get("person_name", "Unknown"),
            "Gate": entry.get("gate_id", "N/A"),
            "Confidence": f"{entry.get('face_match_confidence', 0):.1f}%" if entry.get('face_match_confidence') else "N/A"
        })
    
    df_entries = pd.DataFrame(entry_data)
    st.dataframe(df_entries, use_container_width=True, hide_index=True)

with tab2:
    st.markdown("#### Recent Incidents")
    
    incidents = recent.get("recent_incidents", [])
    
    if incidents:
        incident_data = []
        for inc in incidents[:10]:
            severity_emoji = {
                "low": "🟢",
                "medium": "🟡",
                "high": "🟠",
                "critical": "🔴"
            }
            incident_data.append({
                "ID": inc.get("incident_number", "N/A"),
                "Title": inc.get("title", "N/A"),
                "Severity": f"{severity_emoji.get(inc.get('severity', ''), '⚪')} {inc.get('severity', 'N/A')}",
                "Status": inc.get("status", "N/A"),
                "Created": inc.get("created_at", "N/A")[:19] if inc.get("created_at") else "N/A"
            })
        
        df_incidents = pd.DataFrame(incident_data)
        st.dataframe(df_incidents, use_container_width=True, hide_index=True)
    else:
        # Mock incident data
        mock_incidents = [
            {"ID": "INC-2024-001", "Title": "Suspicious Activity - Block A", "Severity": "🟠 high", "Status": "open", "Created": "2024-01-15 10:30"},
            {"ID": "INC-2024-002", "Title": "Parking Violation", "Severity": "🟢 low", "Status": "in_progress", "Created": "2024-01-15 09:15"},
        ]
        st.dataframe(pd.DataFrame(mock_incidents), use_container_width=True, hide_index=True)

with tab3:
    st.markdown("#### Today's Visitors")
    
    # Try to get visitor data
    try:
        visitors_data = api_client.get_todays_visitors()
        visitors = visitors_data.get("visitors", [])
    except:
        visitors = []
    
    if visitors:
        visitor_data = []
        for v in visitors[:10]:
            status_emoji = {
                "approved": "🟢",
                "checked_in": "🔵",
                "checked_out": "⚪",
                "cancelled": "🔴",
                "expired": "⚫"
            }
            visitor_data.append({
                "Name": v.get("full_name", "N/A"),
                "Type": v.get("visitor_type", "N/A"),
                "Visiting": v.get("visiting_unit", "N/A"),
                "Status": f"{status_emoji.get(v.get('status', ''), '❓')} {v.get('status', 'N/A')}",
                "Code": v.get("approval_code", "N/A")
            })
        
        df_visitors = pd.DataFrame(visitor_data)
        st.dataframe(df_visitors, use_container_width=True, hide_index=True)
    else:
        # Mock visitor data
        mock_visitors = [
            {"Name": "Alice Johnson", "Type": "guest", "Visiting": "A-101", "Status": "🔵 checked_in", "Code": "ABC123"},
            {"Name": "Bob Williams", "Type": "delivery", "Visiting": "B-205", "Status": "🟢 approved", "Code": "XYZ789"},
            {"Name": "Carol Davis", "Type": "service", "Visiting": "C-301", "Status": "⚪ checked_out", "Code": "DEF456"},
        ]
        st.dataframe(pd.DataFrame(mock_visitors), use_container_width=True, hide_index=True)

st.markdown("---")

# Visitor Analytics Section
st.markdown("### 👥 Visitor Analytics")

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### Visitors by Type")
    
    try:
        analytics = api_client.get_visitor_analytics(days=7)
        by_type = analytics.get("by_type", [])
    except:
        by_type = [
            {"type": "guest", "count": 25},
            {"type": "delivery", "count": 15},
            {"type": "service", "count": 8},
            {"type": "cab", "count": 12},
            {"type": "vendor", "count": 5}
        ]
    
    if by_type:
        df_type = pd.DataFrame(by_type)
        fig = px.bar(
            df_type,
            x='type',
            y='count',
            color='type',
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig.update_layout(
            height=250,
            margin=dict(l=0, r=0, t=10, b=0),
            showlegend=False,
            xaxis_title="Visitor Type",
            yaxis_title="Count"
        )
        st.plotly_chart(fig, use_container_width=True)

with col2:
    st.markdown("#### Top Visited Units")
    
    try:
        analytics = api_client.get_visitor_analytics(days=7)
        by_unit = analytics.get("by_unit", [])
    except:
        by_unit = [
            {"unit": "A-101", "count": 8},
            {"unit": "B-205", "count": 6},
            {"unit": "C-301", "count": 5},
            {"unit": "A-203", "count": 4},
            {"unit": "D-102", "count": 3}
        ]
    
    if by_unit:
        df_unit = pd.DataFrame(by_unit)
        fig = px.bar(
            df_unit,
            x='count',
            y='unit',
            orientation='h',
            color='count',
            color_continuous_scale='Blues'
        )
        fig.update_layout(
            height=250,
            margin=dict(l=0, r=0, t=10, b=0),
            showlegend=False,
            xaxis_title="Visitor Count",
            yaxis_title="Unit"
        )
        st.plotly_chart(fig, use_container_width=True)

# Footer
st.markdown("---")
st.caption("Smart Gate Security Command Center | Data refreshes on page reload")
