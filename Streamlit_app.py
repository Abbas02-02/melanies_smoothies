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

# Snowflake connection
cnx = st.connection("Snowflake")
session = cnx.session()

# Cache fruit options (avoid passing session to cache)
@st.cache_data(ttl=600)
def load_fruit_options():
    df = session.table("SMOOTHIES.PUBLIC.FRUIT_OPTIONS") \
                .select(col('FRUIT_NAME'), col('SEARCH_ON')) \
                .to_pandas()
    return df

pd_df = load_fruit_options()

# Multiselect options
fruit_options = pd_df['FRUIT_NAME'].dropna().tolist()
ingredients_list = st.multiselect('Choose up to 5 ingredients:', fruit_options, max_selections=5)

if ingredients_list:
    ingredients_string = ', '.join(ingredients_list)

    for fruit_chosen in ingredients_list:
        row = pd_df.loc[pd_df['FRUIT_NAME'] == fruit_chosen]
        if row.empty:
            st.warning(f"No search key found for {fruit_chosen}.")
            continue

        search_on = row['SEARCH_ON'].iloc[0]
        st.write(f"The search value for **{fruit_chosen}** is **{search_on}**.")

        url = f"https://my.smoothiefroot.com/api/fruit/{search_on}"
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as e:
            st.error(f"Failed to fetch nutrition for {fruit_chosen}: {e}")
            continue

        st.subheader(f"{fruit_chosen} Nutrition Information")
        try:
            data = resp.json()
        except ValueError:
            st.error("The API did not return valid JSON.")
            continue

        if isinstance(data, dict):
            try:
                flat = pd.json_normalize(data)
                st.dataframe(flat, use_container_width=True)
            except Exception:
                st.json(data)
        elif isinstance(data, list):
            try:
                st.dataframe(pd.json_normalize(data), use_container_width=True)
            except Exception:
                st.json(data)
        else:
            st.json(data)

    # Submit order
    time_to_insert = st.button('Submit Order')
    if time_to_insert:
        if not name_on_order:
            st.error("Please enter a name for your smoothie before submitting.")
        else:
            try:
                insert_stmt = f"""
                    INSERT INTO SMOOTHIES.PUBLIC.ORDERS (INGREDIENTS, NAME_ON_ORDER)
                    VALUES ('{ingredients_string}', '{name_on_order}')
                """
                session.sql(insert_stmt).collect()
                st.success('Your Smoothie is ordered! ✅')
            except Exception as e:
                st.error(f"Order submission failed: {e}")
