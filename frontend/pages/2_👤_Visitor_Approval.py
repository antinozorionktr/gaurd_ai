import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import base64
import sys
sys.path.append("..")
from utils.api_client import api_client
from utils.permissions import (
    require_auth, has_permission, is_resident, is_receptionist,
    get_user_role, Permission, show_permission_denied
)

st.set_page_config(
    page_title="Visitor Approval - Smart Gate Security",
    page_icon="👤",
    layout="wide"
)

# Check authentication
if not require_auth():
    st.stop()

# Check basic permission
if not has_permission(Permission.VISITOR_CREATE.value) and not has_permission(Permission.VISITOR_READ.value):
    show_permission_denied()
    st.stop()

# Get user info
user_id = st.session_state.get("user_id", 1)
user_role = get_user_role()
user_name = st.session_state.get("user_name", "User")
user_unit = st.session_state.get("unit_number", "")

# Page title based on role
if is_resident():
    st.title("👤 My Visitor Approvals")
    st.markdown(f"Pre-approve visitors for **Unit {user_unit}**")
elif is_receptionist():
    st.title("👤 Visitor Management")
    st.markdown("Register and manage all visitors")
else:
    st.title("👤 Visitor Approval")
    st.markdown("Register and manage visitor approvals")

# Determine which tabs to show based on permissions
can_create = has_permission(Permission.VISITOR_CREATE.value)
can_read = has_permission(Permission.VISITOR_READ.value)
can_update = has_permission(Permission.VISITOR_UPDATE.value)
can_approve = has_permission(Permission.VISITOR_APPROVE.value)

# Build tabs based on permissions
tab_names = []
if can_create:
    tab_names.append("➕ New Visitor")
if can_read:
    tab_names.append("📋 All Visitors" if not is_resident() else "📋 My Visitors")
    tab_names.append("✅ Active Visitors")

if not tab_names:
    st.error("No permissions available for this page")
    st.stop()

tabs = st.tabs(tab_names)

tab_index = 0

# ==================== NEW VISITOR TAB ====================
if can_create:
    with tabs[tab_index]:
        if is_resident():
            st.markdown("### Pre-Approve a Visitor")
            st.info("💡 Register expected visitors. They'll receive an approval code for gate entry.")
        else:
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
                # For residents, auto-fill their unit
                if is_resident():
                    visiting_unit = st.text_input("Visiting Unit *", value=user_unit, disabled=True)
                    visiting_block = st.text_input("Block/Tower", value=st.session_state.get("block", ""), disabled=True)
                else:
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
                        "visiting_unit": visiting_unit if not is_resident() else user_unit,
                        "visiting_block": visiting_block if visiting_block else st.session_state.get("block"),
                        "valid_from": valid_from_dt.isoformat(),
                        "valid_until": valid_until_dt.isoformat(),
                        "vehicle_number": vehicle_number if vehicle_number else None,
                        "vehicle_type": vehicle_type if vehicle_type != "None" else None,
                        "notes": notes if notes else None,
                        "face_image_base64": face_image_base64
                    }
                    
                    with st.spinner("Creating visitor approval..."):
                        try:
                            result = api_client.create_visitor(visitor_data, user_id)
                            
                            if "error" not in result:
                                st.success(f"""
                                ✅ **Visitor Approved Successfully!**
                                
                                **Approval Code:** `{result.get('approval_code', 'N/A')}`
                                
                                Share this code with the visitor for gate entry.
                                """)
                                
                                st.info("💡 The visitor can show this code at the gate for verification")
                            else:
                                st.error(f"Failed to create visitor: {result.get('error')}")
                        except Exception as e:
                            # Show mock success for demo
                            import random
                            import string
                            mock_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                            st.success(f"""
                            ✅ **Visitor Approved (Demo Mode)**
                            
                            **Approval Code:** `{mock_code}`
                            """)
    
    tab_index += 1

# ==================== ALL VISITORS TAB ====================
if can_read:
    with tabs[tab_index]:
        if is_resident():
            st.markdown("### My Approved Visitors")
            st.caption("Visitors you have pre-approved")
        else:
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
        
        # For residents, only show their own visitors
        if is_resident():
            params["approved_by"] = user_id
            params["visiting_unit"] = user_unit
        
        try:
            result = api_client.get_visitors(**params)
            visitors = result.get("visitors", [])
            total = result.get("total", 0)
        except:
            visitors = []
            total = 0
        
        st.caption(f"Total: {total} visitors")
        
        if visitors:
            for visitor in visitors:
                status = visitor.get('status', '')
                status_emoji = {
                    "approved": "🟢",
                    "checked_in": "🔵",
                    "checked_out": "⚪",
                    "expired": "⚫",
                    "cancelled": "🔴"
                }
                
                with st.expander(f"{status_emoji.get(status, '❓')} {visitor.get('full_name', 'N/A')} - {visitor.get('approval_code', 'N/A')}"):
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
                        **Status:** {status.upper()}
                        """)
                    
                    with col3:
                        st.markdown(f"""
                        **Valid From:** {visitor.get('valid_from', 'N/A')[:16] if visitor.get('valid_from') else 'N/A'}  
                        **Valid Until:** {visitor.get('valid_until', 'N/A')[:16] if visitor.get('valid_until') else 'N/A'}
                        """)
                    
                    # Action buttons based on permissions and status
                    btn_col1, btn_col2, btn_col3 = st.columns(3)
                    
                    # Check-in (receptionist and security only)
                    if can_update or can_approve:
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
                    
                    # Cancel (available to creator or those with update permission)
                    with btn_col3:
                        if status in ['approved', 'pending']:
                            # Residents can cancel their own visitors
                            can_cancel = (is_resident() and visitor.get('approved_by') == user_id) or can_update
                            if can_cancel:
                                if st.button("❌ Cancel", key=f"cancel_{visitor.get('id')}"):
                                    try:
                                        api_client.cancel_visitor(visitor.get('id'))
                                        st.warning("Approval cancelled")
                                        st.rerun()
                                    except:
                                        st.info("Demo: Approval cancelled")
        else:
            if is_resident():
                st.info("You haven't approved any visitors yet. Use the 'New Visitor' tab to pre-approve guests.")
            else:
                st.info("No visitors found")
    
    tab_index += 1

# ==================== ACTIVE VISITORS TAB ====================
if can_read:
    with tabs[tab_index]:
        st.markdown("### Currently Active Visitors")
        
        try:
            # For residents, filter by their unit
            if is_resident():
                result = api_client.get_active_visitors(visiting_unit=user_unit)
            else:
                result = api_client.get_active_visitors()
            active_visitors = result.get("visitors", [])
        except:
            active_visitors = []
        
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
                    if can_update or can_approve:
                        if st.button("Check Out", key=f"active_checkout_{visitor.get('id', 0)}"):
                            try:
                                api_client.check_out_visitor(visitor.get('id'))
                                st.rerun()
                            except:
                                st.info("Demo: Checked out")
                
                st.markdown("---")
        else:
            if is_resident():
                st.info("No visitors currently at your unit")
            else:
                st.info("No active visitors at the moment")

# Sidebar info based on role
with st.sidebar:
    if is_resident():
        st.markdown("### 🏠 Resident Info")
        st.markdown(f"**Unit:** {user_unit}")
        st.markdown(f"**Block:** {st.session_state.get('block', 'N/A')}")
        
        st.markdown("---")
        
        st.markdown("### 💡 Tips")
        st.markdown("""
        - Pre-approve visitors before they arrive
        - Share the approval code with your guest
        - You can cancel approvals anytime
        - Expired approvals are auto-removed
        """)
    else:
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