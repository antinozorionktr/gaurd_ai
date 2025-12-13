import streamlit as st
import pandas as pd
from datetime import datetime
import base64
import os
import sys
sys.path.append("..")
from utils.api_client import api_client
from utils.permissions import (
    require_auth, has_permission, is_resident, is_security_staff, is_admin,
    Permission, show_permission_denied, get_role_display_name
)

st.set_page_config(
    page_title="Watchlist - Smart Gate Security",
    page_icon="⚠️",
    layout="wide"
)

# Check authentication
if not require_auth():
    st.stop()

# Check watchlist permission - Residents and basic users should NOT have access
if not has_permission(Permission.WATCHLIST_READ.value):
    show_permission_denied()
    st.info("Watchlist management is only available to security staff.")
    st.stop()

# Explicitly block residents
if is_resident():
    st.error("🚫 Access Denied")
    st.markdown("Watchlist management is restricted to security personnel only.")
    if st.button("Go to Dashboard"):
        st.switch_page("pages/1_🏠_Dashboard.py")
    st.stop()

st.title("⚠️ Watchlist & Alerts")
st.markdown("Manage flagged individuals and security alerts")

# Get permissions
user_id = st.session_state.get("user_id", 1)
can_create = has_permission(Permission.WATCHLIST_CREATE.value)
can_update = has_permission(Permission.WATCHLIST_UPDATE.value)
can_delete = has_permission(Permission.WATCHLIST_DELETE.value)
can_view_alerts = has_permission(Permission.WATCHLIST_ALERTS.value)

# Helper function to resolve image paths
def get_valid_image_path(image_url):
    """Resolve image path - handles relative paths from backend"""
    if not image_url:
        return None
    
    if os.path.isabs(image_url) and os.path.exists(image_url):
        return image_url
    
    if os.path.exists(image_url):
        return image_url
    
    possible_bases = [
        "../backend",
        "../../backend",
        "/home/priyanshu/Desktop/Hackathon/backend",
        ".",
    ]
    
    for base in possible_bases:
        full_path = os.path.join(base, image_url)
        if os.path.exists(full_path):
            return full_path
    
    return None

# Build tabs based on permissions
tab_names = []
if can_view_alerts:
    tab_names.append("🚨 Active Alerts")
tab_names.append("📋 Watchlist")
if can_create:
    tab_names.append("➕ Add Person")

tabs = st.tabs(tab_names)

tab_index = 0

# ==================== ACTIVE ALERTS TAB ====================
if can_view_alerts:
    with tabs[tab_index]:
        st.markdown("### Active Security Alerts")
        
        # Fetch active alerts
        try:
            alerts_data = api_client.get_active_alerts()
            alerts = alerts_data.get("alerts", [])
        except:
            alerts = []
        
        if alerts:
            st.error(f"🚨 {len(alerts)} Active Alert(s) Requiring Attention!")
            
            for alert in alerts:
                severity = alert.get("severity", "medium")
                severity_colors = {
                    "critical": "🔴",
                    "high": "🟠",
                    "medium": "🟡",
                    "low": "🟢"
                }
                
                with st.container():
                    col1, col2, col3 = st.columns([2, 2, 1])
                    
                    with col1:
                        st.markdown(f"""
                        ### {severity_colors.get(severity, '⚪')} {alert.get('watchlist_person_name', 'Unknown')}
                        **Category:** {alert.get('category', 'N/A').title()}  
                        **Severity:** {severity.upper()}
                        """)
                    
                    with col2:
                        st.markdown(f"""
                        **Gate:** {alert.get('gate_id', 'N/A')}  
                        **Confidence:** {alert.get('confidence_score', 0):.1f}%  
                        **Time:** {alert.get('created_at', 'N/A')[:19] if alert.get('created_at') else 'N/A'}
                        """)
                    
                    with col3:
                        if can_update:
                            if not alert.get("is_acknowledged"):
                                if st.button("✔ Acknowledge", key=f"ack_{alert.get('id')}"):
                                    try:
                                        api_client.acknowledge_alert(
                                            alert.get("id"),
                                            user_id
                                        )
                                        st.success("Alert acknowledged")
                                        st.rerun()
                                    except:
                                        st.success("Demo: Alert acknowledged")
                            
                            if st.button("✅ Resolve", key=f"resolve_{alert.get('id')}"):
                                st.session_state[f"resolve_alert_{alert.get('id')}"] = True
                    
                    # Resolution form (only if permitted)
                    if can_update and st.session_state.get(f"resolve_alert_{alert.get('id')}"):
                        with st.form(f"resolve_form_{alert.get('id')}"):
                            resolution_notes = st.text_area("Resolution Notes")
                            is_false_positive = st.checkbox("Mark as False Positive")
                            
                            if st.form_submit_button("Submit Resolution"):
                                try:
                                    api_client.resolve_alert(
                                        alert.get("id"),
                                        user_id,
                                        resolution_notes,
                                        is_false_positive
                                    )
                                    st.success("Alert resolved")
                                    del st.session_state[f"resolve_alert_{alert.get('id')}"]
                                    st.rerun()
                                except:
                                    st.success("Demo: Alert resolved")
                    
                    st.markdown("---")
        else:
            st.success("✅ No active alerts at this time")
    
    tab_index += 1

# ==================== WATCHLIST TAB ====================
with tabs[tab_index]:
    st.markdown("### Watchlist Database")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        category_filter = st.selectbox(
            "Category",
            options=["All", "banned", "suspicious", "trespasser", "theft", "harassment", "fraud", "violence"],
            format_func=lambda x: x.title()
        )
    with col2:
        severity_filter = st.selectbox(
            "Severity",
            options=["All", "critical", "high", "medium", "low"],
            format_func=lambda x: x.title()
        )
    with col3:
        search = st.text_input("Search", placeholder="Name...")
    
    # Fetch watchlist
    try:
        params = {"is_active": True}
        if category_filter != "All":
            params["category"] = category_filter
        if severity_filter != "All":
            params["severity"] = severity_filter
        
        result = api_client.get_watchlist(**params)
        watchlist = result.get("persons", [])
    except:
        watchlist = []
    
    if watchlist:
        st.caption(f"Total: {len(watchlist)} entries")
        
        for person in watchlist:
            severity = person.get("severity", "medium")
            severity_colors = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🟢"
            }
            
            # Show face status
            has_face = "📸" if person.get('face_image_url') else "👤"
            
            with st.expander(f"{severity_colors.get(severity, '⚪')} {has_face} {person.get('full_name', 'N/A')} - {person.get('category', 'N/A').title()}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"""
                    **Name:** {person.get('full_name', 'N/A')}  
                    **Alias:** {person.get('alias', 'N/A')}  
                    **Phone:** {person.get('phone', 'N/A')}  
                    **Category:** {person.get('category', 'N/A').title()}
                    """)
                
                with col2:
                    face_status = "✅ Face registered" if person.get('face_image_url') else "❌ No face"
                    st.markdown(f"""
                    **Severity:** {severity_colors.get(severity, '⚪')} {severity.upper()}  
                    **Reason:** {person.get('reason', 'N/A')}  
                    **Added:** {person.get('created_at', 'N/A')[:10] if person.get('created_at') else 'N/A'}  
                    **Face:** {face_status}
                    """)
                
                # Image handling
                if person.get('face_image_url'):
                    image_path = get_valid_image_path(person.get('face_image_url'))
                    if image_path:
                        st.image(image_path, width=150)
                    else:
                        st.caption("📷 Image not available locally")
                
                # Delete button (only if permitted)
                if can_delete:
                    if st.button("🗑️ Remove from Watchlist", key=f"remove_{person.get('id')}"):
                        try:
                            api_client.remove_from_watchlist(person.get('id'))
                            st.success("Removed from watchlist")
                            st.rerun()
                        except:
                            st.success("Demo: Removed from watchlist")
    else:
        st.info("No entries in watchlist")

tab_index += 1

# ==================== ADD PERSON TAB ====================
if can_create:
    with tabs[tab_index]:
        st.markdown("### Add Person to Watchlist")
        
        # Initialize session state for face image
        if "watchlist_face_image_base64" not in st.session_state:
            st.session_state.watchlist_face_image_base64 = None
        if "watchlist_face_preview" not in st.session_state:
            st.session_state.watchlist_face_preview = None
        
        # ========== PHOTO CAPTURE SECTION (OUTSIDE FORM) ==========
        st.markdown("---")
        st.markdown("**📷 Photo (for face recognition alerts)**")
        
        photo_option = st.radio(
            "Choose option:",
            ["Upload Photo", "Capture with Camera"],
            horizontal=True,
            key="watchlist_photo_option"
        )
        
        col_photo1, col_photo2 = st.columns([2, 1])
        
        with col_photo1:
            if photo_option == "Upload Photo":
                uploaded_file = st.file_uploader(
                    "Upload photo",
                    type=["jpg", "jpeg", "png"],
                    key="watchlist_upload",
                    help="Clear front-facing photo for best recognition"
                )
                if uploaded_file:
                    # Read and store in session state immediately
                    file_bytes = uploaded_file.read()
                    st.session_state.watchlist_face_image_base64 = base64.b64encode(file_bytes).decode()
                    st.session_state.watchlist_face_preview = file_bytes
                    st.success("✅ Photo captured!")
            else:
                camera_photo = st.camera_input("Take a photo", key="watchlist_camera")
                if camera_photo:
                    # Read and store in session state immediately
                    file_bytes = camera_photo.read()
                    st.session_state.watchlist_face_image_base64 = base64.b64encode(file_bytes).decode()
                    st.session_state.watchlist_face_preview = file_bytes
                    st.success("✅ Photo captured!")
        
        with col_photo2:
            if st.session_state.watchlist_face_preview:
                st.image(st.session_state.watchlist_face_preview, caption="Captured Photo", width=200)
                if st.button("🗑️ Clear Photo", key="clear_watchlist_photo"):
                    st.session_state.watchlist_face_image_base64 = None
                    st.session_state.watchlist_face_preview = None
                    st.rerun()
            else:
                st.info("No photo captured yet")
        
        # Show face status
        if st.session_state.watchlist_face_image_base64:
            st.success(f"📸 Face image ready ({len(st.session_state.watchlist_face_image_base64)} chars)")
        else:
            st.warning("⚠️ No face image - this person won't trigger automatic alerts at gates!")
        
        st.markdown("---")
        
        # ========== PERSON DETAILS FORM ==========
        with st.form("add_watchlist"):
            col1, col2 = st.columns(2)
            
            with col1:
                full_name = st.text_input("Full Name *")
                alias = st.text_input("Known Aliases")
                phone = st.text_input("Phone Number")
                
                category = st.selectbox(
                    "Category *",
                    options=["banned", "suspicious", "trespasser", "theft", "harassment", "fraud", "violence", "other"],
                    format_func=lambda x: x.title()
                )
            
            with col2:
                severity = st.selectbox(
                    "Severity *",
                    options=["critical", "high", "medium", "low"],
                    index=1,
                    format_func=lambda x: x.title()
                )
                
                reason = st.text_area("Reason for Watchlist *", placeholder="Describe why this person should be flagged")
                
                last_known_address = st.text_input("Last Known Address")
                physical_description = st.text_area("Physical Description", placeholder="Height, build, distinguishing features...")
            
            # Show reminder about photo
            if not st.session_state.watchlist_face_image_base64:
                st.warning("⚠️ No photo uploaded. This person will NOT be automatically detected at gates!")
            
            submitted = st.form_submit_button("➕ Add to Watchlist", use_container_width=True, type="primary")
            
            if submitted:
                if not full_name or not reason:
                    st.error("Please fill in required fields (Name, Reason)")
                else:
                    # Get face image from session state (THIS IS THE FIX!)
                    face_image_base64 = st.session_state.watchlist_face_image_base64
                    
                    person_data = {
                        "full_name": full_name,
                        "alias": alias if alias else None,
                        "phone": phone if phone else None,
                        "category": category,
                        "severity": severity,
                        "reason": reason,
                        "last_known_address": last_known_address if last_known_address else None,
                        "physical_description": physical_description if physical_description else None,
                        "face_image_base64": face_image_base64  # From session state!
                    }
                    
                    # Debug: Show what we're sending
                    if face_image_base64:
                        st.info(f"📤 Sending with face image ({len(face_image_base64)} chars)")
                    else:
                        st.warning("📤 Sending WITHOUT face image - no automatic detection!")
                    
                    with st.spinner("Adding to watchlist..."):
                        try:
                            result = api_client.add_to_watchlist(person_data, user_id)
                            
                            if "error" not in result:
                                # Clear the face image from session state after success
                                st.session_state.watchlist_face_image_base64 = None
                                st.session_state.watchlist_face_preview = None
                                
                                st.success(f"✅ {full_name} added to watchlist")
                                
                                # Show face indexing status
                                if result.get('face_image_url'):
                                    st.success("✅ Face registered - automatic gate alerts enabled!")
                                else:
                                    st.warning("⚠️ No face registered - manual identification only")
                            else:
                                st.error(f"Failed: {result.get('error')}")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")

# Alert History (only if can view alerts)
if can_view_alerts:
    st.markdown("---")
    st.markdown("### 📜 Alert History")
    
    try:
        history = api_client.get_alerts(is_resolved=True, limit=20)
        resolved_alerts = history.get("alerts", [])
    except:
        resolved_alerts = []
    
    if resolved_alerts:
        alert_data = []
        for alert in resolved_alerts[:10]:
            alert_data.append({
                "Person": alert.get("watchlist_person_name", "N/A"),
                "Severity": alert.get("severity", "N/A"),
                "Confidence": f"{alert.get('confidence_score', 0):.1f}%",
                "False Positive": "Yes" if alert.get("is_false_positive") else "No",
                "Created": alert.get("created_at", "N/A")[:16] if alert.get("created_at") else "N/A",
                "Resolved": alert.get("resolved_at", "N/A")[:16] if alert.get("resolved_at") else "N/A"
            })
        
        st.dataframe(pd.DataFrame(alert_data), use_container_width=True, hide_index=True)
    else:
        st.info("No resolved alerts in history")

# Sidebar
with st.sidebar:
    st.markdown("### 🔐 Your Access Level")
    st.markdown(f"**Role:** {get_role_display_name(st.session_state.get('user_role', 'unknown'))}")
    
    st.markdown("**Permissions:**")
    st.caption(f"{'✅' if can_view_alerts else '❌'} View Alerts")
    st.caption(f"{'✅' if can_create else '❌'} Add to Watchlist")
    st.caption(f"{'✅' if can_update else '❌'} Update/Resolve")
    st.caption(f"{'✅' if can_delete else '❌'} Remove from Watchlist")
    
    st.markdown("---")
    
    st.markdown("### 📊 Watchlist Stats")
    
    try:
        stats = api_client.get_watchlist()
        total = stats.get("total", 0)
    except:
        total = 0
    
    st.metric("Total Entries", total)
    
    st.markdown("---")
    
    st.markdown("### 🏷️ Categories")
    st.markdown("""
    - **Banned** - Permanently prohibited
    - **Suspicious** - Under observation
    - **Trespasser** - Previous trespassing
    - **Theft** - Theft-related incidents
    - **Harassment** - Harassment cases
    - **Fraud** - Fraud/scam history
    - **Violence** - Violence-related
    """)
    
    st.markdown("---")
    
    st.markdown("### ⚡ Severity Levels")
    st.markdown("""
    - 🔴 **Critical** - Immediate danger
    - 🟠 **High** - Serious concern
    - 🟡 **Medium** - Moderate risk
    - 🟢 **Low** - Minor concern
    """)
    
    st.markdown("---")
    
    st.markdown("### 💡 Tips")
    st.markdown("""
    - **Always upload a photo** for automatic gate detection
    - Without a photo, guards must manually identify
    - Use clear, front-facing photos
    - Higher severity = faster alerts
    """)