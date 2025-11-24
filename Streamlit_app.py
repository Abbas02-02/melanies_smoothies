# Import python packages
import streamlit as st
from snowflake.snowpark.functions import col
import requests

# Write directly to the app
st.title(":cup_with_straw: Customize Your Smoothie :cup_with_straw:")
st.write(
    """Choose the fruits you want in your custom Smoothie!
    """
)

# Name input (kept original label)
name_on_order = st.text_input('Name on Smothie: ')
st.write('The name on your Smoothie will be: ', name_on_order)

# Snowflake connection (kept original lowercase)
cnx = st.connection("snowflake")
session = cnx.session()

# Read fruit options from Snowflake (kept original table path & selection)
my_dataframe = session.table(
    "smoothies.public.fruit_options"
).select(col('FRUIT_NAME'), col('SEARCH_ON'))

# Convert to pandas for lookups (kept original variable name)
pd_df = my_dataframe.to_pandas()

# Multiselect (uses list of fruit names instead of the Snowpark DataFrame)
ingredients_list = st.multiselect(
    "Choose up to 5 ingredients",
    pd_df['FRUIT_NAME'].dropna().tolist(),
    max_selections=5
)

if ingredients_list:

    ingredients_string = ''

    for fruit_chosen in ingredients_list:
        ingredients_string += fruit_chosen + ' '

        # Lookup SEARCH_ON in pandas (kept original style, with a safety check)
        search_rows = pd_df.loc[pd_df['FRUIT_NAME'] == fruit_chosen, 'SEARCH_ON']
        if search_rows.empty or not str(search_rows.iloc[0]).strip():
            st.warning(f"No search key found for {fruit_chosen}.")
            continue

        search_on = str(search_rows.iloc[0]).strip()
        st.write('The search value for ', fruit_chosen, ' is ', search_on, '.')

        # ✅ Use Script 2's API URL, kept in Script 1's call pattern
        url = f"https://my.smoothiefroot.com/api/fruit/{search_on}"
        try:
            fruity_response = requests.get(url, timeout=10)
            fruity_response.raise_for_status()
            data = fruity_response.json()
            # Kept Script 1's 'dataframe' display approach where possible
            if isinstance(data, (dict, list)):
                st.dataframe(data=data, use_container_width=True)
            else:
                st.write(data)
        except Exception as e:
            st.error(f"Failed to fetch nutrition for {fruit_chosen}: {e}")

    # Show ingredients as in original
    st.write(ingredients_string.strip())

    # Insert using Script 1's template string-building style
    my_insert_stmt = """ insert into smoothies.public.orders
    (ingredients, name_on_order)
    values ('""" + ingredients_string.strip() + """', '""" + name_on_order + """')"""

    time_to_insert = st.button('Submit Order')

    if time_to_insert:
        try:
            session.sql(my_insert_stmt).collect()
            st.success('Your Smoothie is ordered, ' + name_on_order + '!', icon="✅")
        except Exception as e:
            st.error(f"Order submission failed: {e}")
