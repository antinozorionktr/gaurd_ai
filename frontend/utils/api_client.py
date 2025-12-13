import requests
from typing import Optional, Dict, Any, List
import streamlit as st
import os

# API Base URL
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api")


class APIClient:
    """Client for interacting with the Smart Gate Security API"""
    
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers including auth token if available"""
        headers = {"Content-Type": "application/json"}
        
        # Add auth token if user is authenticated
        if st.session_state.get("access_token"):
            headers["Authorization"] = f"Bearer {st.session_state.access_token}"
        
        return headers
    
    def _request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        require_auth: bool = True
    ) -> Dict[str, Any]:
        """Make HTTP request to API"""
        url = f"{self.base_url}{endpoint}"
        
        # Check authentication if required
        if require_auth and not st.session_state.get("access_token"):
            return {"error": "Authentication required. Please login."}
        
        try:
            response = requests.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=self._get_headers(),
                timeout=30
            )
            
            # Handle 401 - token expired
            if response.status_code == 401:
                # Try to refresh token
                if self._refresh_token():
                    # Retry request with new token
                    response = requests.request(
                        method=method,
                        url=url,
                        json=data,
                        params=params,
                        headers=self._get_headers(),
                        timeout=30
                    )
                else:
                    # Clear auth and redirect to login
                    self._clear_auth()
                    return {"error": "Session expired. Please login again."}
            
            response.raise_for_status()
            try:
                return response.json()
            except ValueError:
                # Backend returned no/invalid JSON; wrap this as an error response
                return {"error": f"Invalid JSON response (status {response.status_code})"}
            
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            try:
                error_detail = e.response.json().get("detail", error_msg)
            except:
                error_detail = error_msg
            return {"error": error_detail}
    
    def _refresh_token(self) -> bool:
        """Attempt to refresh the access token"""
        refresh_token = st.session_state.get("refresh_token")
        if not refresh_token:
            return False
        
        try:
            response = requests.post(
                f"{self.base_url}/auth/refresh",
                json={"refresh_token": refresh_token},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                st.session_state.access_token = data["access_token"]
                st.session_state.refresh_token = data["refresh_token"]
                return True
        except:
            pass
        
        return False
    
    def _clear_auth(self):
        """Clear authentication data from session"""
        for key in ["authenticated", "access_token", "refresh_token", "user_id", 
                   "user_name", "user_role", "user_email", "permissions"]:
            st.session_state.pop(key, None)
    
    # ==================== Auth ====================
    
    def login(self, email: str, password: str) -> Dict:
        """Login and get tokens"""
        return self._request(
            "POST", "/auth/login",
            data={"email": email, "password": password},
            require_auth=False
        )
    
    def signup(self, user_data: Dict) -> Dict:
        """Register new user"""
        return self._request(
            "POST", "/auth/signup",
            data=user_data,
            require_auth=False
        )
    
    def get_current_user(self) -> Dict:
        """Get current user profile"""
        return self._request("GET", "/auth/me")
    
    def change_password(self, current_password: str, new_password: str) -> Dict:
        """Change current user's password"""
        return self._request(
            "POST", "/auth/me/change-password",
            data={
                "current_password": current_password,
                "new_password": new_password
            }
        )
    
    # ==================== Users (Admin) ====================
    
    def create_user(self, user_data: Dict) -> Dict:
        """Create new user (Admin only)"""
        return self._request("POST", "/auth/users", data=user_data)
    
    def get_users(
        self,
        skip: int = 0,
        limit: int = 50,
        role: Optional[str] = None,
        search: Optional[str] = None
    ) -> Dict:
        """Get users list (Admin only)"""
        params = {"skip": skip, "limit": limit}
        if role:
            params["role"] = role
        if search:
            params["search"] = search
        return self._request("GET", "/auth/users", params=params)
    
    def get_user(self, user_id: int) -> Dict:
        """Get user by ID (Admin only)"""
        return self._request("GET", f"/auth/users/{user_id}")
    
    def update_user(self, user_id: int, update_data: Dict) -> Dict:
        """Update user (Admin only)"""
        return self._request("PUT", f"/auth/users/{user_id}", data=update_data)
    
    def deactivate_user(self, user_id: int) -> Dict:
        """Deactivate user (Admin only)"""
        return self._request("DELETE", f"/auth/users/{user_id}")
    
    # Dashboard
    def get_dashboard_stats(self) -> Dict:
        return self._request("GET", "/dashboard/stats")
    
    def get_recent_activity(self) -> Dict:
        return self._request("GET", "/dashboard/recent-activity")
    
    def get_full_dashboard(self) -> Dict:
        return self._request("GET", "/dashboard/")
    
    def get_entry_trends(self, days: int = 7) -> Dict:
        return self._request("GET", "/dashboard/entry-trends", params={"days": days})
    
    def get_visitor_analytics(self, days: int = 7) -> Dict:
        return self._request("GET", "/dashboard/visitor-analytics", params={"days": days})
    
    def get_incident_summary(self) -> Dict:
        return self._request("GET", "/dashboard/incident-summary")
    
    # Visitors
    def create_visitor(self, visitor_data: Dict, approved_by: int) -> Dict:
        return self._request(
            "POST", "/visitors/",
            data=visitor_data,
            params={"approved_by": approved_by}
        )
    
    def get_visitors(
        self, 
        skip: int = 0, 
        limit: int = 50,
        status: Optional[str] = None,
        search: Optional[str] = None
    ) -> Dict:
        params = {"skip": skip, "limit": limit}
        if status:
            params["status"] = status
        if search:
            params["search"] = search
        return self._request("GET", "/visitors/", params=params)
    
    def get_visitor(self, visitor_id: int) -> Dict:
        return self._request("GET", f"/visitors/{visitor_id}")
    
    def get_visitor_by_code(self, code: str) -> Dict:
        return self._request("GET", f"/visitors/code/{code}")
    
    def get_active_visitors(self) -> Dict:
        return self._request("GET", "/visitors/active")
    
    def get_todays_visitors(self) -> Dict:
        return self._request("GET", "/visitors/today")
    
    def check_in_visitor(self, visitor_id: int) -> Dict:
        return self._request("POST", f"/visitors/{visitor_id}/check-in")
    
    def check_out_visitor(self, visitor_id: int) -> Dict:
        return self._request("POST", f"/visitors/{visitor_id}/check-out")
    
    def cancel_visitor(self, visitor_id: int) -> Dict:
        return self._request("POST", f"/visitors/{visitor_id}/cancel")
    
    # Gate Verification
    def verify_entry(
        self, 
        face_image_base64: str, 
        gate_id: str,
        verified_by: int
    ) -> Dict:
        return self._request(
            "POST", "/gate/verify",
            data={
                "face_image_base64": face_image_base64,
                "gate_id": gate_id
            },
            params={"verified_by": verified_by}
        )
    
    def verify_by_code(
        self, 
        approval_code: str, 
        gate_id: str,
        verified_by: int
    ) -> Dict:
        return self._request(
            "POST", "/gate/verify-code",
            params={
                "approval_code": approval_code,
                "gate_id": gate_id,
                "verified_by": verified_by
            }
        )
    
    def get_entry_logs(
        self,
        skip: int = 0,
        limit: int = 50,
        status: Optional[str] = None
    ) -> Dict:
        params = {"skip": skip, "limit": limit}
        if status:
            params["status"] = status
        return self._request("GET", "/gate/logs", params=params)
    
    def get_todays_logs(self) -> Dict:
        return self._request("GET", "/gate/logs/today")
    
    def manual_allow_entry(
        self,
        entry_log_id: int,
        person_name: str,
        notes: Optional[str] = None
    ) -> Dict:
        params = {"person_name": person_name}
        if notes:
            params["notes"] = notes
        return self._request(
            "POST", f"/gate/manual-allow/{entry_log_id}",
            params=params
        )
    
    def manual_deny_entry(
        self,
        entry_log_id: int,
        denial_reason: str
    ) -> Dict:
        return self._request(
            "POST", f"/gate/manual-deny/{entry_log_id}",
            params={"denial_reason": denial_reason}
        )
    
    # Watchlist
    def add_to_watchlist(self, person_data: Dict, added_by: int) -> Dict:
        return self._request(
            "POST", "/watchlist/persons",
            data=person_data,
            params={"added_by": added_by}
        )
    
    def get_watchlist(
        self,
        skip: int = 0,
        limit: int = 50,
        is_active: bool = True,
        category: Optional[str] = None
    ) -> Dict:
        params = {"skip": skip, "limit": limit, "is_active": is_active}
        if category:
            params["category"] = category
        return self._request("GET", "/watchlist/persons", params=params)
    
    def get_watchlist_person(self, person_id: int) -> Dict:
        return self._request("GET", f"/watchlist/persons/{person_id}")
    
    def remove_from_watchlist(self, person_id: int) -> Dict:
        return self._request("DELETE", f"/watchlist/persons/{person_id}")
    
    def get_active_alerts(self) -> Dict:
        return self._request("GET", "/watchlist/alerts/active")
    
    def get_alerts(
        self,
        skip: int = 0,
        limit: int = 50,
        is_resolved: Optional[bool] = None
    ) -> Dict:
        params = {"skip": skip, "limit": limit}
        if is_resolved is not None:
            params["is_resolved"] = is_resolved
        return self._request("GET", "/watchlist/alerts", params=params)
    
    def acknowledge_alert(self, alert_id: int, acknowledged_by: int) -> Dict:
        return self._request(
            "POST", f"/watchlist/alerts/{alert_id}/acknowledge",
            params={"acknowledged_by": acknowledged_by}
        )
    
    def resolve_alert(
        self,
        alert_id: int,
        resolved_by: int,
        resolution_notes: str,
        is_false_positive: bool = False
    ) -> Dict:
        return self._request(
            "POST", f"/watchlist/alerts/{alert_id}/resolve",
            data={
                "resolution_notes": resolution_notes,
                "is_false_positive": is_false_positive
            },
            params={"resolved_by": resolved_by}
        )
    
    # Incidents
    def create_incident(self, incident_data: Dict, reported_by: int) -> Dict:
        return self._request(
            "POST", "/incidents/",
            data=incident_data,
            params={"reported_by": reported_by}
        )
    
    def get_incidents(
        self,
        skip: int = 0,
        limit: int = 50,
        status: Optional[str] = None,
        severity: Optional[str] = None
    ) -> Dict:
        params = {"skip": skip, "limit": limit}
        if status:
            params["status"] = status
        if severity:
            params["severity"] = severity
        return self._request("GET", "/incidents/", params=params)
    
    def get_incident(self, incident_id: int) -> Dict:
        return self._request("GET", f"/incidents/{incident_id}")
    
    def get_open_incidents(self) -> Dict:
        return self._request("GET", "/incidents/open")
    
    def get_critical_incidents(self) -> Dict:
        return self._request("GET", "/incidents/critical")
    
    def get_incident_stats(self) -> Dict:
        return self._request("GET", "/incidents/stats")
    
    def update_incident(
        self,
        incident_id: int,
        update_data: Dict,
        updated_by: int
    ) -> Dict:
        return self._request(
            "PATCH", f"/incidents/{incident_id}",
            data=update_data,
            params={"updated_by": updated_by}
        )
    
    def assign_incident(
        self,
        incident_id: int,
        assigned_to: int,
        assigned_by: int
    ) -> Dict:
        return self._request(
            "POST", f"/incidents/{incident_id}/assign",
            params={"assigned_to": assigned_to, "assigned_by": assigned_by}
        )
    
    def resolve_incident(
        self,
        incident_id: int,
        resolved_by: int,
        resolution_notes: str
    ) -> Dict:
        return self._request(
            "POST", f"/incidents/{incident_id}/resolve",
            params={
                "resolved_by": resolved_by,
                "resolution_notes": resolution_notes
            }
        )
    
    def add_incident_comment(
        self,
        incident_id: int,
        comment: str,
        created_by: int
    ) -> Dict:
        return self._request(
            "POST", f"/incidents/{incident_id}/comment",
            params={"comment": comment, "created_by": created_by}
        )


# Global API client instance
@st.cache_resource
def get_api_client():
    return APIClient()


api_client = get_api_client()
