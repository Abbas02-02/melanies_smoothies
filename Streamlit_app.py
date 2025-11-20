# Import python packages
import streamlit as st
from snowflake.snowpark.functions import col
import requests
import pandas as pd

# App header
st.title(":cup_with_straw: Customize Your Smoothie! :cup_with_straw:")
st.write("Choose the fruits you want in your custom Smoothie!")

# Name input
name_on_order = st.text_input('Name on Smoothie:')
if name_on_order:
    st.write('The name on your smoothie will be', name_on_order)

# Snowflake connection via Streamlit
# Requires proper st.secrets configuration for "connections.Snowflake"
cnx = st.connection("Snowflake")
session = cnx.session()

# Read fruit options from Snowflake
sf_df = (
    session.table("SMOOTHIES.PUBLIC.FRUIT_OPTIONS")
    .select(col('FRUIT_NAME'), col('SEARCH_ON'))
)
pd_df = sf_df.to_pandas()

# Build options for multiselect
fruit_options = pd_df['FRUIT_NAME'].dropna().tolist()

ingredients_list = st.multiselect(
    'Choose up to 5 ingredients:',
    fruit_options,
    max_selections=5
)

# Show nutrition info for selected fruits
if ingredients_list:
    # Create a clean ingredients string
    ingredients_string = ', '.join(ingredients_list)

    for fruit_chosen in ingredients_list:
        # Lookup search key safely
        row = pd_df.loc[pd_df['FRUIT_NAME'] == fruit_chosen]
        if row.empty:
            st.warning(f"No search key found for {fruit_chosen}.")
            continue

        search_on = row['SEARCH_ON'].iloc[0]
        st.write(f"The search value for **{fruit_chosen}** is **{search_on}**.")

        # Call the external API with proper formatting & error handling
        url = f"https://my.smoothiefroot.com/api/fruit/{search_on}"
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as e:
            st.error(f"Failed to fetch nutrition for {fruit_chosen}: {e}")
            continue

        # Display nutrition info (choose json or dataframe depending on shape)
        st.subheader(f"{fruit_chosen} Nutrition Information")
        try:
            data = resp.json()
        except ValueError:
            st.error("The API did not return valid JSON.")
            continue

        # If it's nested JSON, show raw JSON. If it's flat, tabularize it.
        if isinstance(data, dict):
            # Try to flatten a dict; if it fails, display JSON
            try:
                flat = pd.json_normalize(data)
                st.dataframe(flat, use_container_width=True)
            except Exception:
                st.json(data)
        elif isinstance(data, list):
            # List of dicts -> DataFrame
            st.dataframe(pd.json_normalize(data), use_container_width=True)
        else:
            st.json(data)

    # Prepare SQL insert
    my_insert_stmt = f"""
        INSERT INTO SMOOTHIES.PUBLIC.ORDERS (INGREDIENTS, NAME_ON_ORDER)
        VALUES ('{ingredients_string}', '{name_on_order}')
    """

    # Submit button
    time_to_insert = st.button('Submit Order')
    if time_to_insert:
        if not name_on_order:
            st.error("Please enter a name for your smoothie before submitting.")
        else:
            try:
                session.sql(my_insert_stmt).collect()
                st.success('Your Smoothie is ordered! ✅')
            except Exception as e:
