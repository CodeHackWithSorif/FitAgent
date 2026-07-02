import streamlit as st

from app_utils import *

def render():
    st.title("Load Existing Profile")
    
    db_service = st.session_state.db_service
    all_users = db_service.get_all_users()
    
    if not all_users:
        st.warning("No profiles found. Create a new profile to get started!")
        return
    
    user_options = {f"{u.name} (ID: {u.id})": u.id for u in all_users}
    
    selected = st.selectbox("Select a profile:", list(user_options.keys()))
    
    if st.button("Load Profile", type="primary", use_container_width=True):
        user_id = user_options[selected]
        user = db_service.get_user(user_id)
        
        st.session_state.user_id = user_id
        st.session_state.current_user = user
        
        st.success(f"Loaded profile: {user.name}")
        import time
        time.sleep(0.5)
        set_page("dashboard")
        st.rerun()

