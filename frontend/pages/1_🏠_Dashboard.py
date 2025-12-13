import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
sys.path.append("..")
from utils.api_client import api_client
from utils.permissions import (
    require_auth, has_permission, is_resident, is_receptionist, is_security_staff, is_admin,
    Permission, get_role_display_name
)

st.set_page_config(
    page_title="Dashboard - Smart Gate Security",
    page_icon="🏠",
    layout="wide"
)

# Check authentication
if not require_auth():
    st.stop()

# Check dashboard permission
if not has_permission(Permission.DASHBOARD_VIEW.value):
    st.error("🚫 Access Denied")
    st.stop()

# Get user info
user_id = st.session_state.get("user_id", 1)
user_name = st.session_state.get("user_name", "User")
user_unit = st.session_state.get("unit_number", "")
can_view_analytics = has_permission(Permission.DASHBOARD_ANALYTICS.value)

# Different dashboard views based on role
if is_resident():
    # ==================== RESIDENT DASHBOARD ====================
    st.title(f"🏠 Welcome Home, {user_name}!")
    st.markdown(f"**Unit {user_unit}** • {datetime.now().strftime('%A, %B %d, %Y')}")
    
    st.markdown("---")
    
    # Quick stats for resident
    col1, col2, col3 = st.columns(3)
    
    # Get resident-specific data
    try:
        my_visitors = api_client.get_visitors(approved_by=user_id, visiting_unit=user_unit)
        visitor_count = my_visitors.get("total", 0)
        active_visitors = len([v for v in my_visitors.get("visitors", []) if v.get("status") == "checked_in"])
    except:
        visitor_count = 0
        active_visitors = 0
    
    try:
        my_incidents = api_client.get_incidents(reported_by=user_id)
        incident_count = len(my_incidents.get("incidents", []))
        open_incidents = len([i for i in my_incidents.get("incidents", []) if i.get("status") in ["open", "in_progress"]])
    except:
        incident_count = 0
        open_incidents = 0
    
    with col1:
        st.metric("My Visitors Today", visitor_count)
    with col2:
        st.metric("Currently Inside", active_visitors)
    with col3:
        st.metric("My Open Reports", open_incidents)
    
    st.markdown("---")
    
    # Quick actions for residents
    st.markdown("### 🎯 Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div style="background: linear-gradient(145deg, #4a148c, #7b1fa2); padding: 1.5rem; border-radius: 12px; text-align: center;">
            <h3 style="margin: 0;">👤</h3>
            <p style="color: white; margin: 0.5rem 0;">Pre-Approve Visitor</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Add Visitor", key="dash_add_visitor", use_container_width=True):
            st.switch_page("pages/2_👤_Visitor_Approval.py")
    
    with col2:
        st.markdown("""
        <div style="background: linear-gradient(145deg, #1565c0, #1976d2); padding: 1.5rem; border-radius: 12px; text-align: center;">
            <h3 style="margin: 0;">📋</h3>
            <p style="color: white; margin: 0.5rem 0;">My Visitors</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("View Visitors", key="dash_view_visitors", use_container_width=True):
            st.switch_page("pages/2_👤_Visitor_Approval.py")
    
    with col3:
        st.markdown("""
        <div style="background: linear-gradient(145deg, #b71c1c, #e53935); padding: 1.5rem; border-radius: 12px; text-align: center;">
            <h3 style="margin: 0;">🚨</h3>
            <p style="color: white; margin: 0.5rem 0;">Report Issue</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Report", key="dash_report", use_container_width=True):
            st.switch_page("pages/5_📋_Incidents.py")
    
    st.markdown("---")
    
    # Recent visitors for resident
    st.markdown("### 👥 Recent Visitors")
    
    try:
        recent = api_client.get_visitors(approved_by=user_id, visiting_unit=user_unit, limit=5)
        visitors = recent.get("visitors", [])
    except:
        visitors = []
    
    if visitors:
        for v in visitors[:5]:
            status_emoji = {"approved": "🟢", "checked_in": "🔵", "checked_out": "⚪", "cancelled": "🔴", "expired": "⚫"}
            st.markdown(f"""
            {status_emoji.get(v.get('status', ''), '❓')} **{v.get('full_name', 'N/A')}** - {v.get('visitor_type', '').title()} | Code: `{v.get('approval_code', 'N/A')}`
            """)
    else:
        st.info("No recent visitors. Pre-approve a visitor to get started!")

elif is_receptionist():
    # ==================== RECEPTIONIST DASHBOARD ====================
    st.title("📋 Front Desk Dashboard")
    st.markdown(f"Welcome, **{user_name}** • {datetime.now().strftime('%A, %B %d, %Y')}")
    
    # Auto-refresh option
    col_refresh, col_time = st.columns([1, 3])
    with col_refresh:
        if st.button("🔄 Refresh"):
            st.rerun()
    
    st.markdown("---")
    
    # Today's stats
    try:
        stats = api_client.get_todays_logs()
        log_stats = stats.get("stats", {})
    except:
        log_stats = {}
    
    try:
        visitor_data = api_client.get_todays_visitors()
        today_visitors = visitor_data.get("visitors", [])
    except:
        today_visitors = []
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Expected Today", len(today_visitors))
    with col2:
        checked_in = len([v for v in today_visitors if v.get("status") == "checked_in"])
        st.metric("Currently Inside", checked_in)
    with col3:
        st.metric("Gate Entries", log_stats.get("total", 0))
    with col4:
        st.metric("Alerts", log_stats.get("watchlist_alerts", 0))
    
    st.markdown("---")
    
    # Quick actions
    st.markdown("### ⚡ Quick Actions")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("👤 New Visitor", use_container_width=True, type="primary"):
            st.switch_page("pages/2_👤_Visitor_Approval.py")
    
    with col2:
        if st.button("🚪 Gate Verify", use_container_width=True):
            st.switch_page("pages/3_🚪_Gate_Verification.py")
    
    with col3:
        if st.button("📋 All Visitors", use_container_width=True):
            st.switch_page("pages/2_👤_Visitor_Approval.py")
    
    with col4:
        if st.button("🚨 Report Issue", use_container_width=True):
            st.switch_page("pages/5_📋_Incidents.py")
    
    st.markdown("---")
    
    # Today's visitors table
    st.markdown("### 👥 Today's Visitors")
    
    if today_visitors:
        visitor_data = []
        for v in today_visitors[:10]:
            status_emoji = {"approved": "🟢", "checked_in": "🔵", "checked_out": "⚪", "cancelled": "🔴", "expired": "⚫"}
            visitor_data.append({
                "Name": v.get("full_name", "N/A"),
                "Type": v.get("visitor_type", "N/A").title(),
                "Unit": v.get("visiting_unit", "N/A"),
                "Code": v.get("approval_code", "N/A"),
                "Status": f"{status_emoji.get(v.get('status', ''), '❓')} {v.get('status', 'N/A').title()}"
            })
        st.dataframe(pd.DataFrame(visitor_data), use_container_width=True, hide_index=True)
    else:
        st.info("No visitors scheduled for today")

else:
    # ==================== SECURITY/ADMIN DASHBOARD ====================
    st.title("🛡️ Security Command Dashboard")
    st.markdown(f"Welcome, **{user_name}** ({get_role_display_name(st.session_state.get('user_role', ''))})")
    
    # Auto-refresh option
    col_refresh, col_time = st.columns([1, 3])
    with col_refresh:
        if st.button("🔄 Refresh Data"):
            st.rerun()
    with col_time:
        st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    st.markdown("---")
    
    # Try to fetch data from API
    try:
        dashboard_data = api_client.get_full_dashboard()
        stats = dashboard_data.get("stats", {})
        recent = dashboard_data.get("recent_activity", {})
        api_available = True
    except:
        api_available = False
        stats = {
            "total_visitors_today": 0,
            "active_visitors": 0,
            "total_entries_today": 0,
            "denied_entries_today": 0,
            "active_watchlist_alerts": 0,
            "open_incidents": 0,
            "critical_incidents": 0
        }
        recent = {}
    
    if not api_available:
        st.warning("⚠️ API not available. Showing limited data.")
    
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
            label="Gate Entries",
            value=stats.get("total_entries_today", 0),
            delta=f"-{stats.get('denied_entries_today', 0)} denied",
            delta_color="inverse"
        )
    
    with col3:
        alerts = stats.get("active_watchlist_alerts", 0)
        st.metric(
            label="Active Alerts",
            value=alerts,
            delta="⚠️ Attention" if alerts > 0 else "✅ Clear"
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
                """)
            elif severity == "high":
                st.warning(f"""
                **HIGH ALERT** - {alert.get('watchlist_person_name', 'Unknown')}
                - Gate: {alert.get('gate_id', 'N/A')}
                """)
        
        if not alerts:
            st.info("Alert data loading...")
        
        st.markdown("---")
    
    # Charts (only if analytics permission)
    if can_view_analytics:
        left_col, right_col = st.columns([2, 1])
        
        with left_col:
            st.markdown("### 📈 Entry Trends (Last 7 Days)")
            
            try:
                trends_data = api_client.get_entry_trends(days=7)
                trends = trends_data.get("trends", [])
            except:
                trends = [
                    {"date": (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d"), 
                     "allowed": 100 + i*5, "denied": 5 + i}
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
                    legend=dict(orientation="h", yanchor="bottom", y=1.02)
                )
                
                st.plotly_chart(fig, use_container_width=True)
        
        with right_col:
            st.markdown("### 📋 Incident Summary")
            
            try:
                summary = api_client.get_incident_summary()
                by_severity = summary.get("by_severity", [])
            except:
                by_severity = [
                    {"severity": "low", "count": 2},
                    {"severity": "medium", "count": 3},
                    {"severity": "high", "count": 1}
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
                    showlegend=True
                )
                
                st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Recent Activity
    st.markdown("### 📜 Recent Activity")
    
    tab1, tab2 = st.tabs(["🚪 Gate Entries", "📋 Incidents"])
    
    with tab1:
        try:
            logs_data = api_client.get_todays_logs()
            entries = logs_data.get("logs", [])
        except:
            entries = []
        
        if entries:
            entry_data = []
            for entry in entries[:10]:
                status_emoji = {"allowed": "✅", "denied": "❌", "manual_verification": "⚠️", "watchlist_alert": "🚨"}
                entry_data.append({
                    "Time": entry.get("timestamp", "N/A")[:19] if entry.get("timestamp") else "N/A",
                    "Status": f"{status_emoji.get(entry.get('status', ''), '❓')} {entry.get('status', 'N/A')}",
                    "Person": entry.get("person_name", "Unknown"),
                    "Gate": entry.get("gate_id", "N/A")
                })
            st.dataframe(pd.DataFrame(entry_data), use_container_width=True, hide_index=True)
        else:
            st.info("No entries yet today")
    
    with tab2:
        try:
            incidents_data = api_client.get_incidents(limit=10)
            incidents = incidents_data.get("incidents", [])
        except:
            incidents = []
        
        if incidents:
            incident_data = []
            for inc in incidents[:10]:
                severity_emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}
                incident_data.append({
                    "ID": inc.get("incident_number", "N/A"),
                    "Title": inc.get("title", "N/A"),
                    "Severity": f"{severity_emoji.get(inc.get('severity', ''), '⚪')} {inc.get('severity', 'N/A')}",
                    "Status": inc.get("status", "N/A")
                })
            st.dataframe(pd.DataFrame(incident_data), use_container_width=True, hide_index=True)
        else:
            st.info("No recent incidents")

# Footer
st.markdown("---")
st.caption(f"Smart Gate Security • {get_role_display_name(st.session_state.get('user_role', ''))} Dashboard")