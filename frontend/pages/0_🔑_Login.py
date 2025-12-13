import streamlit as st
import requests
from datetime import datetime

# Must be the first Streamlit command
st.set_page_config(
    page_title="Smart Gate Security - Login",
    page_icon="🔐",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# API Base URL
API_BASE = st.session_state.get("api_base_url", "http://localhost:8000")

# Custom CSS
st.markdown("""
<style>
    /* Hide sidebar on login page */
    [data-testid="stSidebar"] {
        display: none;
    }
    
    /* Center the form */
    .main > div {
        max-width: 450px;
        margin: 0 auto;
        padding-top: 2rem;
    }
    
    /* Card styling */
    .auth-card {
        background: linear-gradient(145deg, #1a1a2e, #16213e);
        padding: 2rem;
        border-radius: 16px;
        border: 1px solid #0f3460;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }
    
    /* Logo area */
    .logo-container {
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .logo-container h1 {
        color: #00d9ff;
        font-size: 1.8rem;
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)


def login(email: str, password: str) -> dict:
    """Call login API"""
    try:
        response = requests.post(
            f"{API_BASE}/api/auth/login",
            json={"email": email, "password": password},
            timeout=10
        )
        return response.json() if response.status_code == 200 else {"error": response.json().get("detail", "Login failed")}
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to server. Please check if the backend is running."}
    except Exception as e:
        return {"error": str(e)}


def signup(data: dict) -> dict:
    """Call signup API"""
    try:
        response = requests.post(
            f"{API_BASE}/api/auth/signup",
            json=data,
            timeout=10
        )
        return response.json() if response.status_code == 201 else {"error": response.json().get("detail", "Signup failed")}
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to server. Please check if the backend is running."}
    except Exception as e:
        return {"error": str(e)}


def store_user_session(result: dict):
    """Store user data in session state"""
    st.session_state.authenticated = True
    st.session_state.access_token = result["access_token"]
    st.session_state.refresh_token = result["refresh_token"]
    st.session_state.user_id = result["user"]["id"]
    st.session_state.user_name = result["user"]["full_name"]
    st.session_state.user_role = result["user"]["role"]
    st.session_state.user_email = result["user"]["email"]
    st.session_state.permissions = result["user"]["permissions"]
    
    # Store unit info for residents
    if result["user"].get("unit_number"):
        st.session_state.unit_number = result["user"]["unit_number"]
    if result["user"].get("block"):
        st.session_state.block = result["user"]["block"]


def main():
    # Check if already logged in
    if st.session_state.get("authenticated"):
        st.success(f"✅ Already logged in as {st.session_state.get('user_name')}")
        
        role = st.session_state.get('user_role', '')
        
        if st.button("Go to Dashboard", type="primary"):
            st.switch_page("pages/1_🏠_Dashboard.py")
        
        if st.button("Logout"):
            for key in ["authenticated", "access_token", "refresh_token", "user_id", 
                       "user_name", "user_role", "user_email", "permissions", 
                       "unit_number", "block"]:
                st.session_state.pop(key, None)
            st.rerun()
        return
    
    # Logo and title
    st.markdown("""
    <div class="logo-container">
        <img src="https://img.icons8.com/fluency/96/security-checked.png" width="80">
        <h1>🔐 Smart Gate Security</h1>
        <p style="color: #888;">AI-Powered Security Command Center</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Tabs for Login/Signup
    tab1, tab2 = st.tabs(["🔑 Login", "📝 Sign Up"])
    
    # ==================== LOGIN TAB ====================
    with tab1:
        st.markdown("### Welcome Back")
        
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="your@email.com")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            
            col1, col2 = st.columns([1, 1])
            with col1:
                remember = st.checkbox("Remember me")
            with col2:
                st.markdown("<div style='text-align:right'><a href='#' style='color:#00d9ff;font-size:0.9rem'>Forgot password?</a></div>", unsafe_allow_html=True)
            
            submitted = st.form_submit_button("Login", use_container_width=True, type="primary")
            
            if submitted:
                if not email or not password:
                    st.error("Please enter email and password")
                else:
                    with st.spinner("Logging in..."):
                        result = login(email, password)
                    
                    if "error" in result:
                        st.error(f"❌ {result['error']}")
                    else:
                        store_user_session(result)
                        
                        st.success(f"✅ Welcome back, {result['user']['full_name']}!")
                        st.balloons()
                        st.rerun()
    
    # ==================== SIGNUP TAB ====================
    with tab2:
        st.markdown("### Create Account")
        
        with st.form("signup_form"):
            full_name = st.text_input("Full Name", placeholder="John Doe")
            signup_email = st.text_input("Email", placeholder="your@email.com", key="signup_email")
            phone = st.text_input("Phone (optional)", placeholder="+91 9876543210")
            
            col1, col2 = st.columns(2)
            with col1:
                signup_password = st.text_input("Password", type="password", placeholder="Min 8 characters", key="signup_pass")
            with col2:
                confirm_password = st.text_input("Confirm Password", type="password", placeholder="••••••••")
            
            role = st.selectbox(
                "Account Type",
                options=["resident", "receptionist"],
                format_func=lambda x: "🏠 Resident" if x == "resident" else "👤 Receptionist"
            )
            
            # Additional fields for residents
            if role == "resident":
                st.markdown("**Resident Details**")
                col1, col2 = st.columns(2)
                with col1:
                    unit_number = st.text_input("Unit Number *", placeholder="A-101")
                with col2:
                    block = st.text_input("Block/Tower", placeholder="Block A")
            else:
                unit_number = None
                block = None
            
            agree = st.checkbox("I agree to the Terms of Service and Privacy Policy")
            
            signup_submitted = st.form_submit_button("Create Account", use_container_width=True, type="primary")
            
            if signup_submitted:
                # Validation
                if not full_name or not signup_email or not signup_password:
                    st.error("Please fill in all required fields")
                elif len(signup_password) < 8:
                    st.error("Password must be at least 8 characters")
                elif signup_password != confirm_password:
                    st.error("Passwords do not match")
                elif role == "resident" and not unit_number:
                    st.error("Please enter your unit number")
                elif not agree:
                    st.error("Please agree to the Terms of Service")
                else:
                    signup_data = {
                        "email": signup_email,
                        "password": signup_password,
                        "full_name": full_name,
                        "phone": phone if phone else None,
                        "role": role,
                        "unit_number": unit_number,
                        "block": block
                    }
                    
                    with st.spinner("Creating account..."):
                        result = signup(signup_data)
                    
                    if "error" in result:
                        st.error(f"❌ {result['error']}")
                    else:
                        store_user_session(result)
                        
                        st.success(f"✅ Account created! Welcome, {result['user']['full_name']}!")
                        st.balloons()
                        st.rerun()
    
    # Demo accounts info
    st.markdown("---")
    st.markdown("### 🧪 Demo Accounts")
    st.markdown("""
    | Role | Email | Password |
    |------|-------|----------|
    | Resident | resident@demo.com | demo1234 |
    | Receptionist | reception@demo.com | demo1234 |
    | Security Guard | guard@demo.com | demo1234 |
    | Admin | admin@demo.com | admin1234 |
    """)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 0.8rem;">
        <p>Need help? Contact your system administrator</p>
        <p>© 2024 Smart Gate Security System</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()