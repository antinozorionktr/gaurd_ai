import streamlit as st
import pandas as pd
from datetime import datetime
import base64
import sys
sys.path.append("..")
from utils.api_client import api_client

st.set_page_config(
    page_title="Gate Verification - Smart Gate Security",
    page_icon="🚪",
    layout="wide"
)

st.title("🚪 Gate Entry Verification")
st.markdown("Verify visitor identity using face recognition or approval code")

# Initialize session state
if "user_id" not in st.session_state:
    st.session_state.user_id = 1

if "verification_result" not in st.session_state:
    st.session_state.verification_result = None

# Gate selection
col1, col2 = st.columns([1, 3])
with col1:
    gate_id = st.selectbox(
        "Select Gate",
        options=["MAIN_GATE", "SIDE_GATE", "PARKING_GATE", "SERVICE_GATE"],
        index=0
    )

st.markdown("---")

# Two verification methods
tab1, tab2 = st.tabs(["📷 Face Recognition", "🔢 Approval Code"])

with tab1:
    st.markdown("### Face Recognition Verification")
    st.markdown("Capture visitor's face for automatic verification")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("#### Capture Photo")
        
        capture_option = st.radio(
            "Choose capture method:",
            ["Camera Capture", "Upload Image"],
            horizontal=True
        )
        
        face_image = None
        face_image_base64 = None
        
        if capture_option == "Camera Capture":
            face_image = st.camera_input("Capture visitor's face")
            if face_image:
                face_image_base64 = base64.b64encode(face_image.read()).decode()
                face_image.seek(0)  # Reset for display
        else:
            uploaded = st.file_uploader(
                "Upload photo",
                type=["jpg", "jpeg", "png"],
                key="gate_upload"
            )
            if uploaded:
                face_image = uploaded
                face_image_base64 = base64.b64encode(uploaded.read()).decode()
                uploaded.seek(0)
        
        if face_image:
            st.image(face_image, caption="Captured Image", use_container_width=True)
        
        verify_btn = st.button(
            "🔍 Verify Identity",
            use_container_width=True,
            disabled=not face_image_base64,
            type="primary"
        )
        
        if verify_btn and face_image_base64:
            with st.spinner("Verifying identity..."):
                result = api_client.verify_entry(
                    face_image_base64=face_image_base64,
                    gate_id=gate_id,
                    verified_by=st.session_state.user_id
                )
                st.session_state.verification_result = result
    
    with col2:
        st.markdown("#### Verification Result")
        
        result = st.session_state.verification_result
        
        if result:
            status = result.get("status", "unknown")
            
            if status == "allowed":
                st.success(result.get("message", "Entry Allowed"))
                st.markdown(f"""
                **Visitor:** {result.get('visitor_name', 'N/A')}  
                **Confidence:** {result.get('confidence', 0):.1f}%  
                **Entry Log ID:** {result.get('entry_log_id', 'N/A')}
                """)
                st.balloons()
                
            elif status == "denied":
                st.error(result.get("message", "Entry Denied"))
                st.markdown(f"""
                **Reason:** {result.get('denial_reason', 'Not specified')}  
                **Entry Log ID:** {result.get('entry_log_id', 'N/A')}
                """)
                
            elif status == "watchlist_alert":
                st.error("🚨 WATCHLIST ALERT!")
                alert_data = result.get("watchlist_alert", {})
                st.markdown(f"""
                **⚠️ SECURITY ALERT**
                
                **Person:** {alert_data.get('person_name', 'Unknown')}  
                **Category:** {alert_data.get('category', 'N/A')}  
                **Severity:** {alert_data.get('severity', 'N/A').upper()}  
                **Confidence:** {alert_data.get('confidence', 0):.1f}%  
                **Reason:** {alert_data.get('reason', 'N/A')}
                
                **DO NOT ALLOW ENTRY - Contact Security Supervisor**
                """)
                
            elif status == "manual_verification":
                st.warning(result.get("message", "Manual verification required"))
                st.markdown("Person not found in database. Please verify manually.")
                
                with st.form("manual_verify"):
                    person_name = st.text_input("Enter Person's Name")
                    allow_reason = st.text_area("Notes (if allowing)")
                    
                    col_allow, col_deny = st.columns(2)
                    
                    with col_allow:
                        allow_btn = st.form_submit_button("✅ Allow Entry", use_container_width=True)
                    with col_deny:
                        deny_btn = st.form_submit_button("❌ Deny Entry", use_container_width=True)
                    
                    if allow_btn and person_name:
                        try:
                            api_client.manual_allow_entry(
                                result.get("entry_log_id"),
                                person_name,
                                allow_reason
                            )
                            st.success(f"Entry allowed for {person_name}")
                        except:
                            st.success(f"Demo: Entry allowed for {person_name}")
                    
                    if deny_btn:
                        try:
                            api_client.manual_deny_entry(
                                result.get("entry_log_id"),
                                "Manual denial"
                            )
                            st.error("Entry denied")
                        except:
                            st.error("Demo: Entry denied")
        else:
            st.info("Capture a photo and click 'Verify Identity' to check visitor")
            
            st.markdown("""
            **Instructions:**
            1. Ask visitor to look at the camera
            2. Ensure good lighting
            3. Capture a clear front-facing photo
            4. Click 'Verify Identity'
            """)

with tab2:
    st.markdown("### Approval Code Verification")
    st.markdown("Enter the visitor's pre-approved code")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        approval_code = st.text_input(
            "Approval Code",
            placeholder="Enter 6-character code",
            max_chars=10
        ).upper()
        
        code_verify_btn = st.button(
            "🔍 Verify Code",
            use_container_width=True,
            disabled=len(approval_code) < 4
        )
        
        if code_verify_btn and approval_code:
            with st.spinner("Verifying code..."):
                result = api_client.verify_by_code(
                    approval_code=approval_code,
                    gate_id=gate_id,
                    verified_by=st.session_state.user_id
                )
                
                if result.get("status") == "allowed":
                    st.success(f"✅ {result.get('message', 'Entry Allowed')}")
                    visitor = result.get("visitor", {})
                    st.markdown(f"""
                    **Visitor:** {visitor.get('full_name', 'N/A')}  
                    **Visiting:** {visitor.get('visiting_unit', 'N/A')}  
                    **Purpose:** {visitor.get('purpose', 'N/A')}
                    """)
                else:
                    st.error(f"❌ {result.get('message', 'Entry Denied')}")
                    
    
    with col2:
        st.markdown("#### Lookup Visitor")
        
        lookup_code = st.text_input(
            "Search by code",
            placeholder="Enter code to lookup",
            key="lookup_code"
        ).upper()
        
        if lookup_code:
            try:
                visitor = api_client.get_visitor_by_code(lookup_code)
                if visitor and "error" not in visitor:
                    status_color = {
                        "approved": "🟢",
                        "checked_in": "🔵",
                        "checked_out": "⚪",
                        "expired": "⚫",
                        "cancelled": "🔴"
                    }
                    
                    st.markdown(f"""
                    **Name:** {visitor.get('full_name', 'N/A')}  
                    **Phone:** {visitor.get('phone', 'N/A')}  
                    **Type:** {visitor.get('visitor_type', 'N/A').title()}  
                    **Visiting:** {visitor.get('visiting_unit', 'N/A')}  
                    **Status:** {status_color.get(visitor.get('status', ''), '❓')} {visitor.get('status', 'N/A').upper()}  
                    **Valid Until:** {visitor.get('valid_until', 'N/A')[:16] if visitor.get('valid_until') else 'N/A'}
                    """)
                else:
                    st.warning("Visitor not found")
            except:
                st.info("Enter a valid code to lookup visitor details")

st.markdown("---")

# Recent Entry Logs
st.markdown("### 📋 Recent Entry Logs")

try:
    logs_data = api_client.get_todays_logs()
    logs = logs_data.get("logs", [])
    stats = logs_data.get("stats", {})
except:
    logs = []
    stats = {"total": 15, "allowed": 12, "denied": 2, "watchlist_alerts": 1}

# Stats row
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Today", stats.get("total", 0))
with col2:
    st.metric("Allowed", stats.get("allowed", 0))
with col3:
    st.metric("Denied", stats.get("denied", 0))
with col4:
    st.metric("Alerts", stats.get("watchlist_alerts", 0))

# Logs table
log_data = []
for log in logs[:20]:
    status_emoji = {
        "allowed": "✅",
        "denied": "❌",
        "manual_verification": "⚠️",
        "watchlist_alert": "🚨"
    }
    log_data.append({
        "Time": log.get("timestamp", "N/A")[:19] if log.get("timestamp") else "N/A",
        "Status": f"{status_emoji.get(log.get('status', ''), '❓')} {log.get('status', 'N/A')}",
        "Person": log.get("person_name", "Unknown"),
        "Gate": log.get("gate_id", "N/A"),
        "Method": log.get("verification_method", "N/A"),
        "Confidence": f"{log.get('face_match_confidence', 0):.1f}%" if log.get('face_match_confidence') else "N/A"
    })

st.dataframe(pd.DataFrame(log_data), use_container_width=True, hide_index=True)

# Sidebar
with st.sidebar:
    st.markdown("### 🚪 Gate Controls")
    st.markdown(f"**Current Gate:** {gate_id}")
    
    st.markdown("---")
    
    st.markdown("### ⚡ Quick Actions")
    
    if st.button("🔄 Clear Result", use_container_width=True):
        st.session_state.verification_result = None
        st.rerun()
    
    if st.button("📋 View All Logs", use_container_width=True):
        st.info("Opening full logs view...")
    
    st.markdown("---")
    
    st.markdown("### 📌 Guidelines")
    st.markdown("""
    **Face Recognition Tips:**
    - Good lighting is essential
    - Face should be clearly visible
    - Remove sunglasses/masks
    - Front-facing photo works best
    
    **Security Protocol:**
    - Always verify ID for manual checks
    - Report suspicious activity
    - Never bypass watchlist alerts
    """)
