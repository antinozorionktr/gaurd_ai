import streamlit as st
import pandas as pd
from datetime import datetime
import base64
import sys
sys.path.append("..")
from utils.api_client import api_client

st.set_page_config(
    page_title="Incidents - Smart Gate Security",
    page_icon="📋",
    layout="wide"
)

st.title("📋 Incident Management")
st.markdown("Report, track, and resolve security incidents")

# Initialize session state
if "user_id" not in st.session_state:
    st.session_state.user_id = 1

# Stats row
try:
    stats = api_client.get_incident_stats()
except:
    stats = {"total": 25, "open": 5, "critical": 1, "resolved_today": 3}

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Incidents", stats.get("total", 0))
with col2:
    st.metric("Open", stats.get("open", 0))
with col3:
    st.metric("Critical", stats.get("critical", 0), delta="Needs attention" if stats.get("critical", 0) > 0 else None)
with col4:
    st.metric("Resolved Today", stats.get("resolved_today", 0))

st.markdown("---")

# Tabs
tab1, tab2, tab3 = st.tabs(["📋 All Incidents", "➕ Report Incident", "🚨 Critical"])

with tab1:
    st.markdown("### Incident List")
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        status_filter = st.selectbox(
            "Status",
            options=["All", "open", "in_progress", "pending_review", "resolved", "closed", "escalated"],
            format_func=lambda x: x.replace("_", " ").title()
        )
    with col2:
        severity_filter = st.selectbox(
            "Severity",
            options=["All", "critical", "high", "medium", "low"],
            format_func=lambda x: x.title()
        )
    with col3:
        category_filter = st.selectbox(
            "Category",
            options=["All", "unauthorized_entry", "theft", "vandalism", "harassment", 
                    "suspicious_activity", "parking_violation", "noise_complaint",
                    "fire_safety", "medical_emergency", "visitor_issue", "equipment_failure", "other"],
            format_func=lambda x: x.replace("_", " ").title()
        )
    with col4:
        search = st.text_input("Search", placeholder="Title or ID...")
    
    # Fetch incidents
    try:
        params = {}
        if status_filter != "All":
            params["status"] = status_filter
        if severity_filter != "All":
            params["severity"] = severity_filter
        if category_filter != "All":
            params["category"] = category_filter
        if search:
            params["search"] = search
        
        result = api_client.get_incidents(**params)
        incidents = result.get("incidents", [])
    except:
        # Mock data
        incidents = [
            {
                "id": 1,
                "incident_number": "INC-2024-001",
                "title": "Suspicious Person - Block A Parking",
                "category": "suspicious_activity",
                "severity": "high",
                "status": "open",
                "location": "Block A - Parking Lot",
                "created_at": "2024-01-15T10:30:00"
            },
            {
                "id": 2,
                "incident_number": "INC-2024-002",
                "title": "Parking Violation - Wrong Spot",
                "category": "parking_violation",
                "severity": "low",
                "status": "in_progress",
                "location": "Block B - Visitor Parking",
                "created_at": "2024-01-15T09:15:00"
            },
            {
                "id": 3,
                "incident_number": "INC-2024-003",
                "title": "Noise Complaint - Late Night Party",
                "category": "noise_complaint",
                "severity": "medium",
                "status": "resolved",
                "location": "Tower C - Unit 501",
                "created_at": "2024-01-14T23:45:00"
            }
        ]
    
    if incidents:
        for incident in incidents:
            severity = incident.get("severity", "medium")
            status = incident.get("status", "open")
            
            severity_colors = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
            status_colors = {
                "open": "🔵",
                "in_progress": "🟣",
                "pending_review": "🟤",
                "resolved": "✅",
                "closed": "⚫",
                "escalated": "🔴"
            }
            
            with st.expander(f"{severity_colors.get(severity, '⚪')} {incident.get('incident_number', 'N/A')} - {incident.get('title', 'N/A')}"):
                col1, col2, col3 = st.columns([2, 2, 1])
                
                with col1:
                    st.markdown(f"""
                    **ID:** {incident.get('incident_number', 'N/A')}  
                    **Title:** {incident.get('title', 'N/A')}  
                    **Category:** {incident.get('category', 'N/A').replace('_', ' ').title()}  
                    **Location:** {incident.get('location', 'N/A')}
                    """)
                
                with col2:
                    st.markdown(f"""
                    **Severity:** {severity_colors.get(severity, '⚪')} {severity.upper()}  
                    **Status:** {status_colors.get(status, '❓')} {status.replace('_', ' ').title()}  
                    **Created:** {incident.get('created_at', 'N/A')[:16] if incident.get('created_at') else 'N/A'}
                    """)
                
                with col3:
                    if status in ['open', 'in_progress']:
                        if st.button("View/Update", key=f"view_{incident.get('id')}"):
                            st.session_state.selected_incident = incident.get('id')
                
                # Show details if selected
                if st.session_state.get('selected_incident') == incident.get('id'):
                    st.markdown("---")
                    st.markdown("**Description:**")
                    st.write(incident.get('description', 'No description provided'))
                    
                    # Update form
                    with st.form(f"update_form_{incident.get('id')}"):
                        new_status = st.selectbox(
                            "Update Status",
                            options=["open", "in_progress", "pending_review", "resolved", "escalated"],
                            index=["open", "in_progress", "pending_review", "resolved", "escalated"].index(status) if status in ["open", "in_progress", "pending_review", "resolved", "escalated"] else 0,
                            format_func=lambda x: x.replace("_", " ").title()
                        )
                        
                        comment = st.text_area("Add Comment/Update")
                        
                        if st.form_submit_button("Update Incident"):
                            try:
                                if new_status != status:
                                    api_client.update_incident(
                                        incident.get('id'),
                                        {"status": new_status},
                                        st.session_state.user_id
                                    )
                                if comment:
                                    api_client.add_incident_comment(
                                        incident.get('id'),
                                        comment,
                                        st.session_state.user_id
                                    )
                                st.success("Incident updated")
                                st.rerun()
                            except:
                                st.success("Demo: Incident updated")
    else:
        st.info("No incidents found matching filters")

with tab2:
    st.markdown("### Report New Incident")
    
    with st.form("incident_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            title = st.text_input("Incident Title *", placeholder="Brief description of the incident")
            
            category = st.selectbox(
                "Category *",
                options=[
                    "unauthorized_entry", "theft", "vandalism", "harassment",
                    "suspicious_activity", "parking_violation", "noise_complaint",
                    "fire_safety", "medical_emergency", "visitor_issue",
                    "equipment_failure", "other"
                ],
                format_func=lambda x: x.replace("_", " ").title()
            )
            
            severity = st.selectbox(
                "Severity *",
                options=["critical", "high", "medium", "low"],
                index=2,
                format_func=lambda x: x.title()
            )
            
            location = st.text_input("Location *", placeholder="e.g., Block A - Ground Floor")
        
        with col2:
            incident_time = st.datetime_input(
                "When did it happen?",
                value=datetime.now()
            )
            
            description = st.text_area(
                "Detailed Description *",
                placeholder="Provide detailed information about the incident...",
                height=150
            )
        
        st.markdown("**Evidence (Optional)**")
        evidence_files = st.file_uploader(
            "Upload photos/evidence",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True
        )
        
        evidence_base64 = []
        if evidence_files:
            for f in evidence_files:
                evidence_base64.append(base64.b64encode(f.read()).decode())
            st.success(f"{len(evidence_files)} file(s) attached")
        
        submitted = st.form_submit_button("📋 Submit Incident Report", use_container_width=True)
        
        if submitted:
            if not title or not description or not location:
                st.error("Please fill in all required fields")
            else:
                incident_data = {
                    "title": title,
                    "description": description,
                    "category": category,
                    "severity": severity,
                    "location": location,
                    "incident_time": incident_time.isoformat() if incident_time else None,
                    "evidence_base64": evidence_base64 if evidence_base64 else None
                }
                
                with st.spinner("Submitting incident report..."):
                    try:
                        result = api_client.create_incident(incident_data, st.session_state.user_id)
                        
                        if "error" not in result:
                            st.success(f"""
                            ✅ **Incident Reported Successfully!**
                            
                            **Incident Number:** `{result.get('incident_number', 'N/A')}`
                            
                            Your report has been logged and will be reviewed.
                            """)
                        else:
                            st.error(f"Failed: {result.get('error')}")
                    except:
                        import random
                        mock_id = f"INC-2024-{random.randint(100, 999)}"
                        st.success(f"""
                        ✅ **Incident Reported (Demo Mode)**
                        
                        **Incident Number:** `{mock_id}`
                        """)

with tab3:
    st.markdown("### 🚨 Critical Incidents")
    st.markdown("Incidents requiring immediate attention")
    
    try:
        critical = api_client.get_critical_incidents()
        critical_incidents = critical.get("incidents", [])
    except:
        critical_incidents = [
            {
                "incident_number": "INC-2024-005",
                "title": "Unauthorized Vehicle in Emergency Lane",
                "category": "fire_safety",
                "status": "open",
                "location": "Main Gate - Emergency Lane",
                "created_at": "2024-01-15T11:00:00"
            }
        ]
    
    if critical_incidents:
        for incident in critical_incidents:
            st.error(f"""
            **🚨 {incident.get('incident_number', 'N/A')}**
            
            **{incident.get('title', 'N/A')}**
            
            Location: {incident.get('location', 'N/A')}  
            Status: {incident.get('status', 'N/A').replace('_', ' ').title()}  
            Reported: {incident.get('created_at', 'N/A')[:16] if incident.get('created_at') else 'N/A'}
            """)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Take Action", key=f"critical_action_{incident.get('id', 0)}"):
                    st.info("Opening incident details...")
            with col2:
                if st.button("Escalate", key=f"critical_escalate_{incident.get('id', 0)}"):
                    try:
                        api_client.update_incident(
                            incident.get('id'),
                            {"status": "escalated"},
                            st.session_state.user_id
                        )
                        st.warning("Incident escalated!")
                    except:
                        st.warning("Demo: Incident escalated!")
            
            st.markdown("---")
    else:
        st.success("✅ No critical incidents at this time")

# Sidebar
with st.sidebar:
    st.markdown("### ⚡ Quick Actions")
    
    if st.button("🆕 New Incident", use_container_width=True):
        st.info("Use the 'Report Incident' tab")
    
    if st.button("📊 View Statistics", use_container_width=True):
        st.info("Opening statistics view...")
    
    st.markdown("---")
    
    st.markdown("### 📊 Quick Stats")
    
    st.markdown(f"""
    - **Open:** {stats.get('open', 0)}
    - **Critical:** {stats.get('critical', 0)}
    - **Resolved Today:** {stats.get('resolved_today', 0)}
    """)
    
    st.markdown("---")
    
    st.markdown("### 🏷️ Categories")
    st.markdown("""
    - 🚫 Unauthorized Entry
    - 🔓 Theft
    - 🎨 Vandalism
    - 😠 Harassment
    - 👁️ Suspicious Activity
    - 🚗 Parking Violation
    - 🔊 Noise Complaint
    - 🔥 Fire Safety
    - 🏥 Medical Emergency
    - 👤 Visitor Issue
    - ⚙️ Equipment Failure
    """)
    
    st.markdown("---")
    
    st.markdown("### 📌 Severity Guide")
    st.markdown("""
    - 🔴 **Critical** - Immediate danger/action required
    - 🟠 **High** - Urgent, needs quick response
    - 🟡 **Medium** - Important but not urgent
    - 🟢 **Low** - Minor issue, routine handling
    """)
