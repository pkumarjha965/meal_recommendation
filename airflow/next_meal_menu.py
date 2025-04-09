import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Page configuration
st.set_page_config(
    page_title="Next Meal Planner",
    page_icon="🍲",
    layout="centered"
)

# Custom CSS for styling
st.markdown("""
<style>
    .main-header {
        font-size: 32px;
        font-weight: bold;
        color: #333333;
        margin-bottom: 10px;
        font-family: 'Helvetica Neue', sans-serif;
    }
    .date-display {
        font-size: 16px;
        color: #555555;
        margin-bottom: 20px;
    }
    .meal-section {
        background-color: #fafafa;
        border-radius: 6px;
        margin-bottom: 15px;
        border: 1px solid #e0e0e0;
        
    }
    .meal-label {
        font-weight: 600;
        color: #666666;
        display: inline-block;
        width: 70px;
    }
    .meal-value {
        color: #333333;
        font-size: 15px;
    }
    .update-button {
        font-size: 13px;
        color: #555555;
        margin-top: 25px;
    }
    .st-emotion-cache-16txtl3 {
        padding: 1rem 1rem 1rem;
    }
</style>
""", unsafe_allow_html=True)


# Internal method to get meal data
def get_meal_data():
    """
    This is an internal method that would normally fetch data from a database or API.
    For this example, we're using a static dictionary.
    In a real application, this would be replaced with actual data retrieval logic.
    """
    # This simulates fetching data from a service
    meal_data = {
        "Monday": {"Lunch": "Aloo Paratha", "Dinner": "Chawal Dal"},
        "Tuesday": {"Lunch": "Vegetable Sandwich", "Dinner": "Paneer Curry with Roti"},
        "Wednesday": {"Lunch": "Chole Bhature", "Dinner": "Rice and Sambar"},
        "Thursday": {"Lunch": "Pasta Salad", "Dinner": "Vegetable Biryani"},
        "Friday": {"Lunch": "Noodles", "Dinner": "Rajma Chawal"},
        "Saturday": {"Lunch": "Pizza", "Dinner": "Palak Paneer with Naan"},
        "Sunday": {"Lunch": "Poha", "Dinner": "Mixed Vegetable Curry with Rice"}
    }
    return meal_data


# Main app layout
col1, col2 = st.columns([5, 1])

with col1:
    # Header section
    st.markdown('<div class="main-header">Next Meal</div>', unsafe_allow_html=True)

# Get today's date and day
today = datetime.now()
day_name = today.strftime("%A")
date_str = today.strftime("%d-%m-%Y")

# Display current day and date
st.markdown(f'<div class="date-display">{day_name} &nbsp;&nbsp;&nbsp; {date_str}</div>', unsafe_allow_html=True)

# Get meal data from internal method
meal_data = get_meal_data()
# Display meal information for today in a styled container
st.markdown('<div class="meal-section">', unsafe_allow_html=True)
st.markdown(
    f'<span class="meal-label">Lunch :</span> <span class="meal-value">{meal_data.get(day_name, {}).get("Lunch", "Not planned")}</span>',
    unsafe_allow_html=True)
st.markdown(
    f'<span class="meal-label">Dinner :</span> <span class="meal-value">{meal_data.get(day_name, {}).get("Dinner", "Not planned")}</span>',
    unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# De-prioritized update menu button
with st.container():
    col1, col2 = st.columns([4, 1])
    with col2:
        st.markdown('<div class="update-button">', unsafe_allow_html=True)
        if st.button("update menu", key="update_button", type="secondary", use_container_width=True):
            st.session_state.show_editor = True
        st.markdown('</div>', unsafe_allow_html=True)

# Menu editor section (de-prioritized and only shown when explicitly requested)
if st.session_state.get("show_editor", False):
    with st.expander("Edit Weekly Menu", expanded=True):
        st.write("This section would allow editing the menu data.")
        st.write("In a real application, this would update the data source.")

        # Simple form to demonstrate the concept
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        selected_day = st.selectbox("Select day to edit:", days)

        lunch = st.text_input("Lunch", value=meal_data.get(selected_day, {}).get("Lunch", ""))
        dinner = st.text_input("Dinner", value=meal_data.get(selected_day, {}).get("Dinner", ""))

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Save Changes"):
                st.success("Menu would be updated in the data source.")
                st.session_state.show_editor = False

        with col2:
            if st.button("Cancel"):
                st.session_state.show_editor = False
