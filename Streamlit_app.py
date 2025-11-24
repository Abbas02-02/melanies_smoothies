import streamlit as st
from snowflake.snowpark.functions import col
import requests

# App header
st.title(":cup_with_straw: Customize Your Smoothie! :cup_with_straw:")
st.write("Choose the fruits you want in your custom Smoothie!")

# Name input
name_on_order = st.text_input('Name on Smoothie:')
if name_on_order:
    st.write('The name on your smoothie will be', name_on_order)

# Snowflake connection
cnx = st.connection("Snowflake")
session = cnx.session()

# Read fruit options from Snowflake
try:
    sf_df = (
        session.table("SMOOTHIES.PUBLIC.FRUIT_OPTIONS")
        .select(col('FRUIT_NAME'), col('SEARCH_ON'))
        .collect()
    )
except Exception as e:
    st.error(f"Failed to load fruit options: {e}")
    st.stop()

# Convert to Python list and dict for lookup
fruit_options = [row['FRUIT_NAME'] for row in sf_df if row['FRUIT_NAME']]
search_lookup = {row['FRUIT_NAME']: row['SEARCH_ON'] for row in sf_df}

# Multiselect for ingredients
ingredients_list = st.multiselect(
    'Choose up to 5 ingredients:',
    fruit_options,
    max_selections=5
)

# Show nutrition info for selected fruits
if ingredients_list:
    ingredients_string = ', '.join(ingredients_list)

    for fruit_chosen in ingredients_list:
        search_on = search_lookup.get(fruit_chosen)
        if not search_on:
            st.warning(f"No search key found for {fruit_chosen}.")
            continue

        st.write(f"The search value for **{fruit_chosen}** is **{search_on}**.")

        # Call external API
        url = f"https://my.smoothiefroot.com/api/fruit/{search_on}"
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as e:
            st.error(f"Failed to fetch nutrition for {fruit_chosen}: {e}")
            continue

        st.subheader(f"{fruit_chosen} Nutrition Information")

        # Parse JSON and display
        try:
            data = resp.json()
        except ValueError:
            st.error("The API did not return valid JSON.")
            continue

        if isinstance(data, dict) or isinstance(data, list):
            st.json(data)
        else:
            st.write(data)

    # Submit button
    time_to_insert = st.button('Submit Order')
    if time_to_insert:
        if not name_on_order:
            st.error("Please enter a name for your smoothie before submitting.")
        else:
            try:
                # ✅ Correct Snowpark insertion using session.sql().collect()
                insert_query = f"""
                INSERT INTO SMOOTHIES.PUBLIC.ORDERS (INGREDIENTS, NAME_ON_ORDER)
                VALUES ('{ingredients}', '{name_on_order}')
                """
                session.sql(insert_query).collect()
                st.success('Your Smoothie is ordered! ✅')
            except Exception as e:
                st.error(f"Order submission failed: {e}")
