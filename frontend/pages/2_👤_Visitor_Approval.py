import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import base64
import sys
sys.path.append("..")
from utils.api_client import api_client

st.set_page_config(
    page_title="Visitor Approval - Smart Gate Security",
    page_icon="👤",
    layout="wide"
)

st.title("👤 Visitor Pre-Approval")
st.markdown("Register and manage visitor approvals")

# Initialize session state
if "user_id" not in st.session_state:
    st.session_state.user_id = 1

# Tabs for different functions
tab1, tab2, tab3 = st.tabs(["➕ New Visitor", "📋 All Visitors", "✅ Active Visitors"])

with tab1:
    st.markdown("### Register New Visitor")
    
    with st.form("visitor_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            full_name = st.text_input("Full Name *", placeholder="Enter visitor's full name")
            phone = st.text_input("Phone Number", placeholder="+91 9876543210")
            email = st.text_input("Email", placeholder="visitor@email.com")
            
            visitor_type = st.selectbox(
                "Visitor Type *",
                options=["guest", "delivery", "service", "cab", "vendor", "other"],
                format_func=lambda x: x.title()
            )
            
            purpose = st.text_input("Purpose of Visit", placeholder="e.g., Family visit, Package delivery")
        
        with col2:
            visiting_unit = st.text_input("Visiting Unit *", placeholder="e.g., A-101")
            visiting_block = st.text_input("Block/Tower", placeholder="e.g., Block A")
            
            # Time window
            st.markdown("**Valid Time Window**")
            col_date1, col_date2 = st.columns(2)
            with col_date1:
                valid_from = st.date_input("From Date", value=datetime.now().date())
                from_time = st.time_input("From Time", value=datetime.now().time())
            with col_date2:
                valid_until = st.date_input("Until Date", value=datetime.now().date() + timedelta(days=1))
                until_time = st.time_input("Until Time", value=datetime.now().time())
            
            vehicle_number = st.text_input("Vehicle Number (Optional)", placeholder="MH 01 AB 1234")
            vehicle_type = st.selectbox(
                "Vehicle Type",
                options=["None", "Car", "Bike", "Auto", "Truck", "Other"]
            )
        
        st.markdown("---")
        
        # Photo capture
        st.markdown("**Visitor Photo (for face recognition)**")
        photo_option = st.radio(
            "Choose option:",
            ["Upload Photo", "Capture with Camera"],
            horizontal=True
        )
        
        face_image_base64 = None
        
        if photo_option == "Upload Photo":
            uploaded_file = st.file_uploader(
                "Upload visitor's photo",
                type=["jpg", "jpeg", "png"],
                help="Clear front-facing photo for best recognition"
            )
            if uploaded_file:
                face_image_base64 = base64.b64encode(uploaded_file.read()).decode()
                st.image(uploaded_file, caption="Uploaded Photo", width=200)
        else:
            camera_photo = st.camera_input("Take a photo")
            if camera_photo:
                face_image_base64 = base64.b64encode(camera_photo.read()).decode()
        
        notes = st.text_area("Additional Notes", placeholder="Any special instructions...")
        
        submitted = st.form_submit_button("✅ Approve Visitor", use_container_width=True)
        
        if submitted:
            if not full_name or not visiting_unit:
                st.error("Please fill in all required fields (Name, Visiting Unit)")
            else:
                # Prepare visitor data
                valid_from_dt = datetime.combine(valid_from, from_time)
                valid_until_dt = datetime.combine(valid_until, until_time)
                
                visitor_data = {
                    "full_name": full_name,
                    "phone": phone if phone else None,
                    "email": email if email else None,
                    "visitor_type": visitor_type,
                    "purpose": purpose if purpose else None,
                    "visiting_unit": visiting_unit,
                    "visiting_block": visiting_block if visiting_block else None,
                    "valid_from": valid_from_dt.isoformat(),
                    "valid_until": valid_until_dt.isoformat(),
                    "vehicle_number": vehicle_number if vehicle_number else None,
                    "vehicle_type": vehicle_type if vehicle_type != "None" else None,
                    "notes": notes if notes else None,
                    "face_image_base64": face_image_base64
                }
                
                with st.spinner("Creating visitor approval..."):
                    try:
                        result = api_client.create_visitor(visitor_data, st.session_state.user_id)
                        
                        if "error" not in result:
                            st.success(f"""
                            ✅ **Visitor Approved Successfully!**
                            
                            **Approval Code:** `{result.get('approval_code', 'N/A')}`
                            
                            Share this code with the visitor for gate entry.
                            """)
                            
                            # Show QR code placeholder
                            st.info("💡 The visitor can show this code at the gate for verification")
                        else:
                            st.error(f"Failed to create visitor: {result.get('error')}")
                    except Exception as e:
                        st.error(f"API Error: {str(e)}")
                        # Show mock success for demo
                        import random
                        import string
                        mock_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                        st.success(f"""
                        ✅ **Visitor Approved (Demo Mode)**
                        
                        **Approval Code:** `{mock_code}`
                        """)

with tab2:
    st.markdown("### All Visitors")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        status_filter = st.selectbox(
            "Filter by Status",
            options=["All", "approved", "checked_in", "checked_out", "expired", "cancelled"],
            format_func=lambda x: x.title() if x != "All" else x
        )
    with col2:
        search_term = st.text_input("Search", placeholder="Name or code...")
    with col3:
        if st.button("🔄 Refresh"):
            st.rerun()
    
    # Fetch visitors
    params = {}
    if status_filter != "All":
        params["status"] = status_filter
    if search_term:
        params["search"] = search_term
    
    result = api_client.get_visitors(**params)
    visitors = result.get("visitors", [])
    total = result.get("total", 0)
    
    st.caption(f"Total: {total} visitors")
    
    if visitors:
        for visitor in visitors:
            with st.expander(f"👤 {visitor.get('full_name', 'N/A')} - {visitor.get('approval_code', 'N/A')}"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown(f"""
                    **Name:** {visitor.get('full_name', 'N/A')}  
                    **Phone:** {visitor.get('phone', 'N/A')}  
                    **Type:** {visitor.get('visitor_type', 'N/A').title()}
                    """)
                
                with col2:
                    st.markdown(f"""
                    **Visiting:** {visitor.get('visiting_unit', 'N/A')}  
                    **Code:** `{visitor.get('approval_code', 'N/A')}`  
                    **Status:** {visitor.get('status', 'N/A').upper()}
                    """)
                
                with col3:
                    st.markdown(f"""
                    **Valid From:** {visitor.get('valid_from', 'N/A')[:16] if visitor.get('valid_from') else 'N/A'}  
                    **Valid Until:** {visitor.get('valid_until', 'N/A')[:16] if visitor.get('valid_until') else 'N/A'}
                    """)
                
                # Action buttons
                status = visitor.get('status', '')
                btn_col1, btn_col2, btn_col3 = st.columns(3)
                
                with btn_col1:
                    if status == 'approved':
                        if st.button("✅ Check In", key=f"checkin_{visitor.get('id')}"):
                            try:
                                api_client.check_in_visitor(visitor.get('id'))
                                st.success("Checked in!")
                                st.rerun()
                            except:
                                st.info("Demo: Visitor checked in")
                
                with btn_col2:
                    if status == 'checked_in':
                        if st.button("🚪 Check Out", key=f"checkout_{visitor.get('id')}"):
                            try:
                                api_client.check_out_visitor(visitor.get('id'))
                                st.success("Checked out!")
                                st.rerun()
                            except:
                                st.info("Demo: Visitor checked out")
                
                with btn_col3:
                    if status in ['approved', 'pending']:
                        if st.button("❌ Cancel", key=f"cancel_{visitor.get('id')}"):
                            try:
                                api_client.cancel_visitor(visitor.get('id'))
                                st.warning("Approval cancelled")
                                st.rerun()
                            except:
                                st.info("Demo: Approval cancelled")
    else:
        st.info("No visitors found")

with tab3:
    st.markdown("### Currently Active Visitors")
    
    result = api_client.get_active_visitors()
    active_visitors = result.get("visitors", [])
    
    if active_visitors:
        st.metric("Active Visitors", len(active_visitors))
        
        for visitor in active_visitors:
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            
            with col1:
                st.markdown(f"**{visitor.get('full_name', 'N/A')}**")
            with col2:
                st.markdown(f"Unit: {visitor.get('visiting_unit', 'N/A')}")
            with col3:
                checked_in = visitor.get('checked_in_at', '')
                if checked_in:
                    st.markdown(f"Since: {checked_in[:16]}")
            with col4:
                if st.button("Check Out", key=f"active_checkout_{visitor.get('id', 0)}"):
                    try:
                        api_client.check_out_visitor(visitor.get('id'))
                        st.rerun()
                    except:
                        st.info("Demo: Checked out")
            
            st.markdown("---")
    else:
        st.info("No active visitors at the moment")

# Sidebar info
with st.sidebar:
    st.markdown("### 📌 Quick Info")
    st.markdown("""
    **Visitor Types:**
    - 👥 Guest - Personal visitors
    - 📦 Delivery - Package/food delivery
    - 🔧 Service - Plumber, electrician, etc.
    - 🚕 Cab - Taxi/ride services
    - 🏪 Vendor - Regular service providers
    """)
    
    st.markdown("---")
    st.markdown("""
    **Status Meaning:**
    - 🟢 Approved - Waiting to arrive
    - 🔵 Checked In - Currently inside
    - ⚪ Checked Out - Has left
    - 🔴 Cancelled - Approval revoked
    - ⚫ Expired - Time window passed
    """)
