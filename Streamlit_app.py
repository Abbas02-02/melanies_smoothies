import streamlit as st
from snowflake.snowpark.functions import col
import requests

st.title("Customize Your Smoothie :cup_with_straw:")
st.write("Choose the fruits you want in your custom Smoothie!")

# --- Name on order ---
name_on_order = st.text_input("Name on Smoothie", placeholder="e.g., Happi")
if name_on_order:
    st.caption(f"The name on your smoothie will be: **{name_on_order}**")

# --- Connect to Snowflake ---
try:
    # If using secrets.toml, this is enough:
    cnx = st.connection("snowflake")
    session = cnx.session()

    # --- Load fruit options as a dictionary ---
    # Expect table: SMOOTHIES.PUBLIC.FRUIT_OPTIONS with columns FRUIT_NAME, SEARCH_ON
    fruit_df = (
        session.table("SMOOTHIES.PUBLIC.FRUIT_OPTIONS")
        .select(col("FRUIT_NAME"), col("SEARCH_ON"))
        .collect()
    )
    # Build mapping: fruit name -> search key
    fruit_map = {row["FRUIT_NAME"]: row["SEARCH_ON"] for row in fruit_df}
    fruit_names = sorted(fruit_map.keys())

    # --- Ingredient selection ---
    ingredients_list = st.multiselect(
        "Choose up to 5 ingredients:",
        options=fruit_names,
        max_selections=5,
        help="Pick your favorite fruits",
    )

    if ingredients_list:
        st.subheader("Fruit Info")
        for fruit_chosen in ingredients_list:
            search_on = fruit_map.get(fruit_chosen)
            if not search_on:
                st.warning(f"No search key found for {fruit_chosen}.")
                continue

            try:
                fruityvice_response = requests.get(
                    f"https://my.smoothiefroot.com/api/fruit/{search_on}",
                    timeout=8,
                )
                fruityvice_response.raise_for_status()
                data = fruityvice_response.json()

                # Show the JSON content nicely
                st.json(data)

            except requests.exceptions.HTTPError as e:
                st.warning(f"API returned an error for {fruit_chosen}: {e}")
            except requests.exceptions.RequestException as e:
                st.error(f"Failed to fetch details for {fruit_chosen}: {e}")

        # --- Submit order ---
        ingredients_string = " ".join(ingredients_list)

        # Disable button until we have a name and at least one ingredient
        time_to_insert = st.button(
            "Submit Order",
            disabled=(not name_on_order or len(ingredients_list) == 0),
        )

        if time_to_insert:
            try:
                # Parameterized insert to avoid SQL injection
                session.sql(
                    "INSERT INTO SMOOTHIES.PUBLIC.ORDERS(INGREDIENTS, NAME_ON_ORDER) "
                    "VALUES (?, ?)",
                    params=[ingredients_string, name_on_order],
                ).collect()

                st.success(f"Your Smoothie is ordered, {name_on_order}! ✅")
            except Exception as e:
                st.error(f"Failed to submit order: {e}")

except Exception as ex:
    st.error(f"An error occurred: {ex}")
    st.info(
        "Tip: Ensure you configured the Snowflake connection in `.streamlit/secrets.toml` "
        "or passed connection kwargs to `st.connection()`."
    )
