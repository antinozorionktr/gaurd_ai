import streamlit as st
import pandas as pd
from datetime import datetime
import base64
import sys
sys.path.append("..")
from utils.api_client import api_client

st.set_page_config(
    page_title="Watchlist - Smart Gate Security",
    page_icon="⚠️",
    layout="wide"
)

st.title("⚠️ Watchlist & Alerts")
st.markdown("Manage flagged individuals and security alerts")

# Initialize session state
if "user_id" not in st.session_state:
    st.session_state.user_id = 1

# Tabs
tab1, tab2, tab3 = st.tabs(["🚨 Active Alerts", "📋 Watchlist", "➕ Add Person"])

with tab1:
    st.markdown("### Active Security Alerts")
    
    # Fetch active alerts
    try:
        alerts_data = api_client.get_active_alerts()
        alerts = alerts_data.get("alerts", [])
    except:
        # Mock alerts
        alerts = [
            {
                "id": 1,
                "watchlist_person_name": "John Suspicious",
                "category": "suspicious",
                "severity": "high",
                "gate_id": "MAIN_GATE",
                "confidence_score": 87.5,
                "is_acknowledged": False,
                "created_at": "2024-01-15T14:30:00"
            }
        ]
    
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
                    if not alert.get("is_acknowledged"):
                        if st.button("✓ Acknowledge", key=f"ack_{alert.get('id')}"):
                            try:
                                api_client.acknowledge_alert(
                                    alert.get("id"),
                                    st.session_state.user_id
                                )
                                st.success("Alert acknowledged")
                                st.rerun()
                            except:
                                st.success("Demo: Alert acknowledged")
                    
                    if st.button("✅ Resolve", key=f"resolve_{alert.get('id')}"):
                        st.session_state[f"resolve_alert_{alert.get('id')}"] = True
                
                # Resolution form
                if st.session_state.get(f"resolve_alert_{alert.get('id')}"):
                    with st.form(f"resolve_form_{alert.get('id')}"):
                        resolution_notes = st.text_area("Resolution Notes")
                        is_false_positive = st.checkbox("Mark as False Positive")
                        
                        if st.form_submit_button("Submit Resolution"):
                            try:
                                api_client.resolve_alert(
                                    alert.get("id"),
                                    st.session_state.user_id,
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

with tab2:
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
        # Mock data
        watchlist = [
            {
                "id": 1,
                "full_name": "John Suspicious",
                "alias": "Johnny",
                "category": "suspicious",
                "severity": "high",
                "reason": "Multiple unauthorized entry attempts",
                "is_active": True,
                "created_at": "2024-01-10T10:00:00"
            },
            {
                "id": 2,
                "full_name": "Jane Banned",
                "alias": None,
                "category": "banned",
                "severity": "critical",
                "reason": "Theft incident - permanently banned",
                "is_active": True,
                "created_at": "2024-01-05T15:30:00"
            }
        ]
    
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
            
            with st.expander(f"{severity_colors.get(severity, '⚪')} {person.get('full_name', 'N/A')} - {person.get('category', 'N/A').title()}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"""
                    **Name:** {person.get('full_name', 'N/A')}  
                    **Alias:** {person.get('alias', 'N/A')}  
                    **Phone:** {person.get('phone', 'N/A')}  
                    **Category:** {person.get('category', 'N/A').title()}
                    """)
                
                with col2:
                    st.markdown(f"""
                    **Severity:** {severity_colors.get(severity, '⚪')} {severity.upper()}  
                    **Reason:** {person.get('reason', 'N/A')}  
                    **Added:** {person.get('created_at', 'N/A')[:10] if person.get('created_at') else 'N/A'}
                    """)
                
                if person.get('face_image_url'):
                    st.image(person.get('face_image_url'), width=150)
                
                if st.button("🗑️ Remove from Watchlist", key=f"remove_{person.get('id')}"):
                    try:
                        api_client.remove_from_watchlist(person.get('id'))
                        st.success("Removed from watchlist")
                        st.rerun()
                    except:
                        st.success("Demo: Removed from watchlist")
    else:
        st.info("No entries in watchlist")

with tab3:
    st.markdown("### Add Person to Watchlist")
    
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
        
        st.markdown("**Photo (for face recognition)**")
        photo_option = st.radio(
            "Choose option:",
            ["Upload Photo", "Capture with Camera"],
            horizontal=True,
            key="watchlist_photo"
        )
        
        face_image_base64 = None
        
        if photo_option == "Upload Photo":
            uploaded_file = st.file_uploader(
                "Upload photo",
                type=["jpg", "jpeg", "png"],
                key="watchlist_upload"
            )
            if uploaded_file:
                face_image_base64 = base64.b64encode(uploaded_file.read()).decode()
                st.image(uploaded_file, caption="Uploaded Photo", width=200)
        else:
            camera_photo = st.camera_input("Take a photo", key="watchlist_camera")
            if camera_photo:
                face_image_base64 = base64.b64encode(camera_photo.read()).decode()
        
        submitted = st.form_submit_button("➕ Add to Watchlist", use_container_width=True)
        
        if submitted:
            if not full_name or not reason:
                st.error("Please fill in required fields (Name, Reason)")
            else:
                person_data = {
                    "full_name": full_name,
                    "alias": alias if alias else None,
                    "phone": phone if phone else None,
                    "category": category,
                    "severity": severity,
                    "reason": reason,
                    "last_known_address": last_known_address if last_known_address else None,
                    "physical_description": physical_description if physical_description else None,
                    "face_image_base64": face_image_base64
                }
                
                with st.spinner("Adding to watchlist..."):
                    try:
                        result = api_client.add_to_watchlist(person_data, st.session_state.user_id)
                        
                        if "error" not in result:
                            st.success(f"✅ {full_name} added to watchlist")
                        else:
                            st.error(f"Failed: {result.get('error')}")
                    except:
                        st.success(f"Demo: {full_name} added to watchlist")

# Alert History
st.markdown("---")
st.markdown("### 📜 Alert History")

try:
    history = api_client.get_alerts(is_resolved=True, limit=20)
    resolved_alerts = history.get("alerts", [])
except:
    resolved_alerts = [
        {
            "id": 10,
            "watchlist_person_name": "Past Alert Person",
            "severity": "medium",
            "confidence_score": 75.5,
            "is_false_positive": True,
            "created_at": "2024-01-14T10:00:00",
            "resolved_at": "2024-01-14T10:30:00"
        }
    ]

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
    st.markdown("### 📊 Watchlist Stats")
    
    try:
        stats = api_client.get_watchlist()
        total = stats.get("total", 0)
    except:
        total = 15
    
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
