import streamlit as st
import pandas as pd
from datetime import datetime
import base64
import sys
sys.path.append("..")
from utils.api_client import api_client
from utils.permissions import (
    require_auth, has_permission, is_resident, is_receptionist, is_security_staff, is_admin,
    Permission, show_permission_denied, get_role_display_name
)

st.set_page_config(
    page_title="Incidents - Smart Gate Security",
    page_icon="📋",
    layout="wide"
)

# Check authentication
if not require_auth():
    st.stop()

# Check incident permissions
if not has_permission(Permission.INCIDENT_READ.value) and not has_permission(Permission.INCIDENT_CREATE.value):
    show_permission_denied()
    st.stop()

# Get user info and permissions
user_id = st.session_state.get("user_id", 1)
user_name = st.session_state.get("user_name", "User")
can_create = has_permission(Permission.INCIDENT_CREATE.value)
can_read = has_permission(Permission.INCIDENT_READ.value)
can_update = has_permission(Permission.INCIDENT_UPDATE.value)
can_assign = has_permission(Permission.INCIDENT_ASSIGN.value)

# Page title based on role
if is_resident():
    st.title("📋 Report & Track Issues")
    st.markdown("Report security concerns and track your submissions")
elif is_receptionist():
    st.title("📋 Incident Reports")
    st.markdown("Log and view incident reports")
else:
    st.title("📋 Incident Management")
    st.markdown("Report, track, and resolve security incidents")

# Stats row (different for residents vs staff)
if not is_resident():
    try:
        stats = api_client.get_incident_stats()
    except:
        stats = {"total": 0, "open": 0, "critical": 0, "resolved_today": 0}
    
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

# Build tabs based on permissions
tab_names = []
if can_create:
    tab_names.append("➕ Report Incident" if is_resident() else "➕ Report Incident")
if can_read:
    tab_names.append("📋 My Reports" if is_resident() else "📋 All Incidents")
if is_security_staff() or is_admin():
    tab_names.append("🚨 Critical")

tabs = st.tabs(tab_names)

tab_index = 0

# ==================== REPORT INCIDENT TAB ====================
if can_create:
    with tabs[tab_index]:
        if is_resident():
            st.markdown("### Report a Security Concern")
            st.info("💡 Use this form to report any security concerns, suspicious activity, or issues in your building.")
        else:
            st.markdown("### Report New Incident")
        
        with st.form("incident_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                title = st.text_input("Incident Title *", placeholder="Brief description of the incident")
                
                # Simplified categories for residents
                if is_resident():
                    category_options = [
                        "suspicious_activity", "noise_complaint", "parking_violation",
                        "visitor_issue", "equipment_failure", "other"
                    ]
                else:
                    category_options = [
                        "unauthorized_entry", "theft", "vandalism", "harassment",
                        "suspicious_activity", "parking_violation", "noise_complaint",
                        "fire_safety", "medical_emergency", "visitor_issue",
                        "equipment_failure", "other"
                    ]
                
                category = st.selectbox(
                    "Category *",
                    options=category_options,
                    format_func=lambda x: x.replace("_", " ").title()
                )
                
                # Simplified severity for residents
                if is_resident():
                    severity = st.selectbox(
                        "How urgent is this?",
                        options=["low", "medium", "high"],
                        index=1,
                        format_func=lambda x: {
                            "low": "🟢 Not urgent - Can wait",
                            "medium": "🟡 Somewhat urgent",
                            "high": "🟠 Urgent - Needs attention soon"
                        }.get(x, x.title())
                    )
                else:
                    severity = st.selectbox(
                        "Severity *",
                        options=["critical", "high", "medium", "low"],
                        index=2,
                        format_func=lambda x: x.title()
                    )
                
                location = st.text_input(
                    "Location *", 
                    placeholder="e.g., Block A - Ground Floor",
                    value=f"Unit {st.session_state.get('unit_number', '')}" if is_resident() else ""
                )
            
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
            
            submitted = st.form_submit_button("📋 Submit Report", use_container_width=True)
            
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
                    
                    with st.spinner("Submitting report..."):
                        try:
                            result = api_client.create_incident(incident_data, user_id)
                            
                            if "error" not in result:
                                st.success(f"""
                                ✅ **Report Submitted Successfully!**
                                
                                **Reference Number:** `{result.get('incident_number', 'N/A')}`
                                
                                {"Our team will review your report and take appropriate action." if is_resident() else "The incident has been logged and will be reviewed."}
                                """)
                            else:
                                st.error(f"Failed: {result.get('error')}")
                        except:
                            import random
                            mock_id = f"INC-2024-{random.randint(100, 999)}"
                            st.success(f"""
                            ✅ **Report Submitted (Demo Mode)**
                            
                            **Reference Number:** `{mock_id}`
                            """)
    
    tab_index += 1

# ==================== ALL INCIDENTS TAB ====================
if can_read:
    with tabs[tab_index]:
        if is_resident():
            st.markdown("### My Submitted Reports")
            st.caption("Track the status of your reports")
        else:
            st.markdown("### Incident List")
        
        # Filters (simplified for residents)
        if is_resident():
            col1, col2 = st.columns(2)
            with col1:
                status_filter = st.selectbox(
                    "Status",
                    options=["All", "open", "in_progress", "resolved"],
                    format_func=lambda x: x.replace("_", " ").title()
                )
            with col2:
                if st.button("🔄 Refresh"):
                    st.rerun()
        else:
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
            if not is_resident():
                if severity_filter != "All":
                    params["severity"] = severity_filter
                if category_filter != "All":
                    params["category"] = category_filter
                if search:
                    params["search"] = search
            else:
                # For residents, only show their own reports
                params["reported_by"] = user_id
            
            result = api_client.get_incidents(**params)
            incidents = result.get("incidents", [])
        except:
            incidents = []
        
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
                        # Update buttons only for staff with permissions
                        if can_update and status in ['open', 'in_progress']:
                            if st.button("Update", key=f"view_{incident.get('id')}"):
                                st.session_state.selected_incident = incident.get('id')
                    
                    # Description
                    if incident.get('description'):
                        st.markdown("**Description:**")
                        st.write(incident.get('description', 'No description provided'))
                    
                    # Update form (only for staff with update permission)
                    if can_update and st.session_state.get('selected_incident') == incident.get('id'):
                        st.markdown("---")
                        
                        with st.form(f"update_form_{incident.get('id')}"):
                            new_status = st.selectbox(
                                "Update Status",
                                options=["open", "in_progress", "pending_review", "resolved", "escalated"],
                                index=["open", "in_progress", "pending_review", "resolved", "escalated"].index(status) if status in ["open", "in_progress", "pending_review", "resolved", "escalated"] else 0,
                                format_func=lambda x: x.replace("_", " ").title()
                            )
                            
                            comment = st.text_area("Add Comment/Update")
                            
                            # Assignment (only for those with assign permission)
                            if can_assign:
                                assign_to = st.text_input("Assign to (User ID)", placeholder="Enter user ID")
                            
                            if st.form_submit_button("Update Incident"):
                                try:
                                    if new_status != status:
                                        api_client.update_incident(
                                            incident.get('id'),
                                            {"status": new_status},
                                            user_id
                                        )
                                    if comment:
                                        api_client.add_incident_comment(
                                            incident.get('id'),
                                            comment,
                                            user_id
                                        )
                                    st.success("Incident updated")
                                    st.rerun()
                                except:
                                    st.success("Demo: Incident updated")
        else:
            if is_resident():
                st.info("You haven't submitted any reports yet. Use the 'Report Incident' tab to submit a new report.")
            else:
                st.info("No incidents found matching filters")
    
    tab_index += 1

# ==================== CRITICAL TAB ====================
if is_security_staff() or is_admin():
    with tabs[tab_index]:
        st.markdown("### 🚨 Critical Incidents")
        st.markdown("Incidents requiring immediate attention")
        
        try:
            critical = api_client.get_critical_incidents()
            critical_incidents = critical.get("incidents", [])
        except:
            critical_incidents = []
        
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
                        st.session_state.selected_incident = incident.get('id')
                        st.info("Opening incident details...")
                with col2:
                    if can_update:
                        if st.button("Escalate", key=f"critical_escalate_{incident.get('id', 0)}"):
                            try:
                                api_client.update_incident(
                                    incident.get('id'),
                                    {"status": "escalated"},
                                    user_id
                                )
                                st.warning("Incident escalated!")
                            except:
                                st.warning("Demo: Incident escalated!")
                
                st.markdown("---")
        else:
            st.success("✅ No critical incidents at this time")

# Sidebar
with st.sidebar:
    if is_resident():
        st.markdown("### 📞 Emergency Contacts")
        st.markdown("""
        - **Security Office:** Ext. 100
        - **Emergency:** 911
        - **Building Manager:** Ext. 200
        """)
        
        st.markdown("---")
        
        st.markdown("### 💡 When to Report")
        st.markdown("""
        - Suspicious persons/activity
        - Noise disturbances
        - Parking violations
        - Maintenance issues
        - Visitor problems
        - Equipment malfunctions
        """)
    else:
        st.markdown("### ⚡ Quick Actions")
        
        if can_create:
            if st.button("🆕 New Incident", use_container_width=True):
                st.info("Use the 'Report Incident' tab")
        
        st.markdown("---")
        
        st.markdown("### 🔐 Your Access")
        st.markdown(f"**Role:** {get_role_display_name(st.session_state.get('user_role', 'unknown'))}")
        st.caption(f"{'✅' if can_create else '❌'} Create incidents")
        st.caption(f"{'✅' if can_update else '❌'} Update incidents")
        st.caption(f"{'✅' if can_assign else '❌'} Assign incidents")
        
        st.markdown("---")
        
        st.markdown("### 🏷️ Categories")
        st.markdown("""
        - 🚫 Unauthorized Entry
        - 🔓 Theft
        - 🎨 Vandalism
        - 😠 Harassment
        - 👁️ Suspicious Activity
        - 🚗 Parking Violation
        - 📊 Noise Complaint
        - 🔥 Fire Safety
        - 🏥 Medical Emergency
        - 👤 Visitor Issue
        - ⚙️ Equipment Failure
        """)