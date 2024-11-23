import streamlit as st
import pandas as pd
import numpy as np
import re
from datetime import datetime


# Include risk calculation functions here
def calculate_economic_zone_score(economic_zone):
    economic_zone_scores = {
        'Dubai Department of Economic Development': 15,
        'Abu Dhabi Department for Economic Development': 15,
        'Head Office-Fujairah Municipality': 5,
        'Masdar': 5,
        'Sharjah Economic Development Department': 15,
        'ADAFZ': 10,
        'ADGM': 30,
        'Ajman Department of Economic Development': 15,
        'Ajman Media City Free Zone': 10,
        'DAFZA': 10,
        'DCCA': 10,
        'Department of Economic Development in Abu Dhabi': 15,
        'Department of Economic Development in Dubai': 15,
        'DHCC': 10,
        'Dibba Municipality': 5,
        'DIFC': 30,
        'DMCC': 10,
        'DSO': 10,
        'Dubai CommerCity': 10,
        'Dubai Department of Economy & Tourism': 10,
        'DWTC': 10,
        'Fujairah Free Zone': 10,
        'Hamriyah Free Zone Authority': 5,
        'Dubai South': 5,
        'Jafza': 10,
        'KIZAD': 10,
        'Meydan': 5,
        'Ras Al Khaimah Department of Economic Development': 15,
        'Ras Al Khaimah Economic Zone': 15,
        'Saif Free Zone': 10,
        'Sharjah Media City': 5,
        'Sharjah Publishing City Free Zone': 5,
        'Trakhees Dubai FZ': 10,
        'TRAKHEES-Department of Planning and Development': 10,
        'Umm Al Quwain Department of Economic Development': 15,
        'Umm Al Quwain Free Trade Zone': 5
    }
    return economic_zone_scores.get(economic_zone, 0)


def calculate_date_of_operations_score(est_date, expiry_date):
    if pd.isnull(est_date) or pd.isnull(expiry_date):
        return 0
    est_date = pd.to_datetime(est_date)
    expiry_date = pd.to_datetime(expiry_date)
    years_of_operation = (expiry_date - est_date).days / 365.25
    if years_of_operation > 3:
        return 15
    elif 1 <= years_of_operation <= 3:
        return 5
    return 0


def calculate_status_score(status):
    return 10 if status == 'Active' else -50


def calculate_legal_type_score(legal_type):
    legal_type_scores = {
        'Branch of a foreign establishment': 20,
        'Branch of Company Registered in other emirates': 5,
        'Civil Company': 20,
        'Companie Branches': 5,
        'Establishments': 5,
        'Limited Liability Company': 5,
        'Single Person Company': 0,
        'Branch of Company Registered in free zone': 20,
        'Branch of Foreign Company': 20,
        'Branch of Local Company': 5,
        'Company limited by shares': 5,
        'Cooperative societies': 5,
        'Free Zone Company': 5,
        'Free Zone Company Branch': 5,
        'Free Zone Corporate': 5,
        'Free Zone Establishment': 5,
        'GCC Company Branch': 5,
        'Limited Liability Company - Single Owner(LLC - SO)': 5,
        'Private Shareholding Company': 20,
        'Public Shareholding Company': 20
    }
    return legal_type_scores.get(legal_type, 0)


def calculate_wps_score(wps_status):
    wps_status = str(wps_status).upper()
    if wps_status in ['PRIVATE', 'N', 'N/', 'N/A', 'NA', '']:
        return 10

    negative_patterns = [
        '*SALARY STAMENT,', '*STOP NEW WORK PERMIT - WPS', 'CANCEL COMPANY',
        '*COMPANY HAVING FINE,', '*TAWTEEN - NEW WP BLOCK,',
        '*STOPPED FOR EXPIRED LABOUR CARD FOR MORE THAN 6 MONTHS,',
        '*COMMUNICATION INFO REQUIRED,', '*HIGH RISK COMPANY,',
        '*TRANSACTION OF LABOUR CARD IS PENDING IN MOL,',
        '*WORKPERMIT UNDER CANCELLATION MORE THAN ONE MONTH,',
        '*WORKPERMIT UNDER CANCELLATION MORE THAN SIX MONTHS,',
        'NO ACTIVE OWNERS;', 'NO AUTHORIZED OWNER;', 'NO ACTIVE ESIGNATURE CARD;',
        'NO TRADES FOR THE COMPANY;', '*COMPANY BLOCKED FOR LABOUR CAMP REQUIREMENT,',
        '*COMPANY HAS FINE INSTALLMENTS,', '*STOPPED BY ADPF,',
        '*INSTALLMENT NOT PAID AT TIME,'
    ]

    for pattern in negative_patterns:
        if pattern in wps_status:
            return -10

    return 0


def calculate_visa_number_score(visa_approved, visa_cancelled):
    visa_number = visa_approved + visa_cancelled
    if pd.isnull(visa_number):
        return 0  # NA case
    if visa_number > 50:
        return 20  # More than 50 Visas
    elif visa_number > 0:
        return 10  # Less than 50 Visas (but more than 0)
    else:
        return 0  # 0 Visas


def calculate_visa_ratio_score(visa_approved, visa_cancelled, visa_requested, visa_used):
    visa_score = 0
    total_visas = visa_approved + visa_cancelled
    if total_visas > 0:
        cancellation_ratio = visa_cancelled / total_visas if total_visas > 0 else 0
        unused_ratio = (visa_approved - visa_used) / visa_approved if visa_approved > 0 else 0
        request_approval_ratio = visa_requested / visa_approved if visa_approved > 0 else float('inf')

        if cancellation_ratio > 0.3:
            visa_score -= 15
        if unused_ratio > 0.5:
            visa_score -= 10
        if request_approval_ratio > 2:
            visa_score -= 5

        if visa_approved > 50 and visa_used / visa_approved > 0.8:
            visa_score += 10

    return visa_score


def calculate_phone_score(phone_number):
    if pd.isnull(phone_number):
        return 0

    # Convert to string, handling potential float values
    phone_str = str(phone_number)

    # Remove any decimal point and following digits
    phone_str = phone_str.split('.')[0]

    # Strip any whitespace and remove any non-digit characters
    phone_str = ''.join(filter(str.isdigit, phone_str.strip()))

    if not phone_str:
        return 0

    # Check for UAE cell phone numbers
    if phone_str.startswith('9715') or (phone_str.startswith('05') and len(phone_str) == 10):
        return 5  # UAE cell phone

    # Check for other UAE numbers (assumed to be landlines)
    if phone_str.startswith('971') or phone_str.startswith('0'):
        return 20  # UAE landline

    return 5  # Other international number


def calculate_website_score(website):
    if pd.isnull(website) or str(website).strip() == '':
        return 0
    return 10


def calculate_email_score(email):
    if pd.isnull(email) or str(email).strip() == '':
        return -10  # Penalize if email is not found

    email = str(email).lower().strip()

    # List of common public email domains
    public_domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com']

    # Check if the email uses a public domain
    if any(email.endswith('@' + domain) for domain in public_domains):
        return -5  # Penalize if email is from a public domain

    # Check if it's a valid email format and not a public domain
    if re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email) and not any(
            email.endswith('@' + domain) for domain in public_domains):
        return 5  # Reward if it's a valid email with a company domain

    return 0  # Neutral score for any other case


def calculate_branch_score(is_branch):
    return 5 if is_branch.lower() == 'yes' else 0


def calculate_risk_scores(features, weights):
    scores = {}
    scores['Economic Zone'] = calculate_economic_zone_score(features['economic_department']) * weights[
        'Economic Zone']
    scores['Date of Operations'] = calculate_date_of_operations_score(features['est_date'],
                                                                      features['expiry_date']) * weights[
                                       'Date of Operations']
    scores['Status'] = calculate_status_score(features['status']) * weights['Status']
    scores['Legal Type'] = calculate_legal_type_score(features['legal_type']) * weights['Legal Type']
    scores['WPS'] = calculate_wps_score(features['wps']) * weights['WPS']
    scores['Visa Number'] = calculate_visa_number_score(features['visa_approved'], features['visa_cancelled']) * \
                            weights['Visa Number']
    scores['Visa Ratio'] = calculate_visa_ratio_score(features['visa_approved'], features['visa_cancelled'],
                                                      features['visa_requested'], features['visa_used']) * weights[
                               'Visa Ratio']
    phone_number = features['phone_no'] if pd.notnull(features['phone_no']) else features['mobile_no']
    scores['Phone'] = calculate_phone_score(phone_number) * weights['Phone']
    scores['Website'] = calculate_website_score(features['website_url']) * weights['Website']
    scores['Email'] = calculate_email_score(features['email']) * weights['Email']
    scores['Branch'] = calculate_branch_score(features['is_branch']) * weights['Branch']
    scores['Total'] = sum(scores.values())
    return scores

# Set up page configuration with a modern theme
st.set_page_config(
    page_title="Company Risk Score Calculator",
    layout="wide",
    page_icon="📊",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "This application calculates risk scores for companies based on various parameters."
    }
)

# Apply custom CSS for styling
st.markdown("""
    <style>
        /* Import fonts */
        @import url('https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;600;700&display=swap');

        /* General Settings */
        body {
            font-family: 'Open Sans', sans-serif;
            background-color: #F9F9F9;
        }

        /* Main Header */
        .main-header {
            font-size: 2.5em;
            color: #264653;
            font-weight: 700;
            margin-bottom: 20px;
        }

        /* Sub Header */
        .sub-header {
            font-size: 1.75em;
            color: #2A9D8F;
            font-weight: 600;
            margin-top: 30px;
            margin-bottom: 15px;
        }

        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background-color: #ADD8E6;  /* Light blue background */
            padding: 20px;
            color: #000000;  /* Set text color to black for readability */
        }

        /* Sidebar Headers */
        [data-testid="stSidebar"] h2 {
            color: #000000;
            font-weight: 700;
            font-size: 1.5em;
            margin-top: 20px;
            margin-bottom: 10px;
        }

        /* Input Widgets in Sidebar */
        [data-testid="stSidebar"] label {
            color: #000000;
            font-weight: 600;
            margin-top: 10px;
            font-size: 0.9em;
        }

        /* Input Widgets Styling */
        [data-testid="stSidebar"] .stSelectbox > div > div,
        [data-testid="stSidebar"] .stTextInput > div > div,
        [data-testid="stSidebar"] .stDateInput > div > div,
        [data-testid="stSidebar"] .stSlider > div {
            background-color: #ADD8E6;  /* Match sidebar background */
            color: #000000;
            border-radius: 5px;
            border: 1px solid #000000; /* Black border */
        }

        /* Number Input Styling (Visa Numbers) */
        [data-testid="stSidebar"] .stNumberInput > div {
            background-color: #ADD8E6;  /* Match sidebar background */
            border: 1px solid #000000; /* Black border */
            border-radius: 5px;
            padding: 5px;
        }
        [data-testid="stSidebar"] .stNumberInput input {
            background-color: #ADD8E6 !important;  /* Match sidebar background */
            color: #000000 !important;
            border: none !important;
        }

        /* Datepicker Styling */
        [data-testid="stSidebar"] .stDateInput input {
            background-color: #ADD8E6 !important;  /* Match sidebar background */
            color: #000000 !important;
            border: 1px solid #000000 !important; /* Black border */
            height: 40px; /* Increase height if needed */
        }

        /* Slider Styling */
        [data-testid="stSidebar"] .stSlider > div {
            background-color: #ADD8E6;  /* Match sidebar background */
            border: 2px solid #000000;  /* Thicker black border */
            border-radius: 5px;
            padding: 5px;
        }
        [data-testid="stSidebar"] .stSlider > div > div > div {
            color: #000000;
        }

        /* Adjusting the Button Position */
        .stButton button {
            margin-top: 10px;  /* Reduced margin to raise the button */
        }

        /* Button Styling */
        .stButton button {
            background-color: #e76f51;
            color: #ffffff;
            border-radius: 5px;
            border: none;
            padding: 0.6em 1.2em;
            font-size: 1em;
            font-weight: 600;
            cursor: pointer;
            transition: background-color 0.3s ease;
            width: 100%;
        }
        .stButton button:hover {
            background-color: #f4a261;
        }

        /* Score Card */
        .score-card {
            border: 1px solid #264653;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
            background-color: #e9f5f2;
        }

        /* DataFrame Styling */
        .styled-table {
            border-collapse: collapse;
            margin: 25px 0;
            font-size: 1em;
            font-family: 'Open Sans', sans-serif;
            min-width: 400px;
            width: 100%;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.15);
        }
        .styled-table thead tr {
            background-color: #2A9D8F;
            color: #ffffff;
            text-align: left;
        }
        .styled-table th, .styled-table td {
            padding: 12px 15px;
        }
        .styled-table tbody tr {
            border-bottom: 1px solid #dddddd;
        }
        .styled-table tbody tr:nth-of-type(even) {
            background-color: #f3f3f3;
        }
        .styled-table tbody tr:last-of-type {
            border-bottom: 2px solid #2A9D8F;
        }
        .styled-table tbody tr.active-row {
            font-weight: bold;
            color: #2A9D8F;
        }

        /* Expander Styling */
        .st-expander {
            background-color: #FFFFFF;
            border: 1px solid #264653;
            border-radius: 8px;
            padding: 10px;
        }

        /* Metric Styling */
        .stMetric {
            font-size: 1.5em;
            font-weight: 700;
            color: #264653;
        }
    </style>
""", unsafe_allow_html=True)

# Main title and introduction
st.markdown("<h1 class='main-header'>📊 Company Risk Score Calculator</h1>", unsafe_allow_html=True)
st.write(
    "This application helps calculate a risk score for companies based on different parameters such as economic zone, legal type, visa status, and more.")

# Load data using cached function
@st.cache_data
def load_data():
    df_org = pd.read_excel('./data/appro-companies.xlsx',
                           usecols=['business_name_english', 'economic_department', 'status', 'legal_type', 'wps',
                                    'est_date', 'expiry_date', 'visa_approved', 'visa_cancelled', 'visa_requested',
                                    'visa_used', 'phone_no', 'mobile_no', 'website_url', 'email', 'is_branch'],
                           engine='openpyxl')
    df_extended = pd.read_csv('./data/3k_extended.csv',
                              usecols=['business_name_english', 'economic_department', 'status', 'legal_type', 'wps',
                                       'est_date', 'expiry_date', 'visa_approved', 'visa_cancelled', 'visa_requested',
                                       'visa_used', 'phone_no', 'mobile_no', 'website_url', 'email', 'is_branch'])
    df = pd.concat([df_org, df_extended], ignore_index=True)
    return df

# Load data
df = load_data()

# Sidebar for inputs
st.sidebar.markdown("<h2 style='color: #000000;'>🔍 Company Selection and Feature Weights</h2>", unsafe_allow_html=True)

# User selects features for the company
st.sidebar.markdown("<h3 style='color: #000000;'>Select Company</h3>", unsafe_allow_html=True)
selected_company_name = st.sidebar.selectbox("Business Name:", df['business_name_english'].unique())

# Populate features based on selected company
selected_company = df[df['business_name_english'] == selected_company_name].iloc[0]

# User inputs and modifications for the selected company features
st.sidebar.markdown("<h3 style='color: #000000;'>Company Details</h3>", unsafe_allow_html=True)
features = {}

for column in ['economic_department', 'status', 'legal_type', 'wps', 'is_branch']:
    options = df[column].dropna().unique()
    default_index = list(options).index(selected_company[column]) if selected_company[column] in options else 0
    features[column] = st.sidebar.selectbox(
        f"{column.replace('_', ' ').title()}:",
        options,
        index=default_index,
        help=f"Select the {column.replace('_', ' ')} of the company."
    )

# Adjusted code for visa number inputs
for column in ['visa_approved', 'visa_cancelled', 'visa_requested', 'visa_used']:
    features[column] = st.sidebar.number_input(
        f"{column.replace('_', ' ').title()}:",
        value=int(selected_company[column] or 0),
        min_value=0,
        step=1,
        format="%d",
        help=f"Enter the {column.replace('_', ' ')}."
    )

for column in ['phone_no', 'mobile_no', 'website_url', 'email']:
    placeholder = f"{column.replace('_', ' ').title()}:"
    features[column] = st.sidebar.text_input(
        placeholder,
        value=str(selected_company[column] or ""),
        help=f"Enter the company's {column.replace('_', ' ')}."
    )

features['est_date'] = st.sidebar.date_input(
    "Establishment Date:",
    value=pd.to_datetime(selected_company['est_date']) if pd.notnull(
        selected_company['est_date']) else datetime.today(),
    help="Select the establishment date."
)
features['expiry_date'] = st.sidebar.date_input(
    "Expiry Date:",
    value=pd.to_datetime(selected_company['expiry_date']) if pd.notnull(
        selected_company['expiry_date']) else datetime.today(),
    help="Select the expiry date."
)

# User selects weights for each feature with default values
st.sidebar.markdown("<h3 style='color: #000000;'>Feature Weights</h3>", unsafe_allow_html=True)
weights = {
    'Economic Zone': st.sidebar.slider("Economic Zone Weight:", 0.0, 1.0, 0.15,
                                       help="Adjust the weight for Economic Zone."),
    'Date of Operations': st.sidebar.slider("Date of Operations Weight:", 0.0, 1.0, 0.30,
                                            help="Adjust the weight for Date of Operations."),
    'Status': st.sidebar.slider("Status Weight:", 0.0, 1.0, 0.10, help="Adjust the weight for Status."),
    'Legal Type': st.sidebar.slider("Legal Type Weight:", 0.0, 1.0, 0.10, help="Adjust the weight for Legal Type."),
    'WPS': st.sidebar.slider("WPS Weight:", 0.0, 1.0, 0.05, help="Adjust the weight for WPS."),
    'Visa Number': st.sidebar.slider("Visa Number Weight:", 0.0, 1.0, 0.30, help="Adjust the weight for Visa Number."),
    'Visa Ratio': st.sidebar.slider("Visa Ratio Weight:", 0.0, 1.0, 0.30, help="Adjust the weight for Visa Ratio."),
    'Phone': st.sidebar.slider("Phone Weight:", 0.0, 1.0, 0.10, help="Adjust the weight for Phone."),
    'Website': st.sidebar.slider("Website Weight:", 0.0, 1.0, 0.10, help="Adjust the weight for Website."),
    'Email': st.sidebar.slider("Email Weight:", 0.0, 1.0, 0.10, help="Adjust the weight for Email."),
    'Branch': st.sidebar.slider("Branch Weight:", 0.0, 1.0, 0.10, help="Adjust the weight for Branch status.")
}

# Main content layout
st.markdown("<h2 class='sub-header'>Company Details and Risk Score Calculation</h2>", unsafe_allow_html=True)

# Create a row with two columns
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("### Selected Company Information")
    # Use expander to show/hide company details
    with st.expander("View Company Details"):
        updated_company = pd.DataFrame.from_dict(features, orient='index', columns=['Value'])
        updated_company.index.rename('Feature', inplace=True)
        updated_company.reset_index(inplace=True)

        # Style the DataFrame
        styled_company = updated_company.style.set_properties(**{
            'background-color': 'white',
            'color': 'black',
            'border-color': '#dddddd',
            'border-style': 'solid',
            'border-width': '1px',
            'font-size': '16px',
            'text-align': 'left',
            'padding': '8px',
        }).set_table_styles([
            {'selector': 'th', 'props': [
                ('font-size', '18px'),
                ('text-align', 'left'),
                ('background-color', '#2A9D8F'),
                ('color', '#ffffff'),
                ('padding', '12px')
            ]},
            {'selector': 'td', 'props': [('padding', '12px')]},
            {'selector': 'tr:nth-child(even)', 'props': [('background-color', '#f3f3f3')]},
        ]).set_table_attributes('class="styled-table"')

        st.write(styled_company.to_html(), unsafe_allow_html=True)

with col2:
    st.markdown("### Calculate Risk Score")
    # Place the "Calculate Risk Score" button here to align with "View Company Details"
    if st.button("Calculate Risk Score"):
        risk_scores = calculate_risk_scores(features, weights)
        st.session_state['risk_scores'] = risk_scores

# Now display risk scores
st.markdown("### Risk Scores")

if 'risk_scores' in st.session_state:
    risk_scores = st.session_state['risk_scores']
    # Display total risk score prominently
    st.metric(label="Total Risk Score", value=f"{risk_scores['Total']:.1f}")

    # Use progress bar to visualize risk score (assuming a max score for normalization)
    max_score = 100  # Define max score based on your scoring system
    score_percentage = min(max(risk_scores['Total'] / max_score, 0), 1)
    st.progress(score_percentage)

    # Convert risk_scores to DataFrame
    risk_scores_df = pd.DataFrame(list(risk_scores.items()), columns=['Parameter', 'Score'])
    risk_scores_df = risk_scores_df[risk_scores_df['Parameter'] != 'Total']  # Exclude Total

    # Apply conditional formatting to risk scores
    def highlight_scores(val):
        # Convert val to numeric, setting non-numeric values to NaN
        num_val = pd.to_numeric(val, errors='coerce')
        if pd.isnull(num_val):
            color = 'black'  # Default color for NaN or non-numeric values
        elif num_val > 0:
            color = 'green'
        elif num_val < 0:
            color = 'red'
        else:
            color = 'black'  # For zero
        return f'color: {color}'

    styled_scores = risk_scores_df.style.format({'Score': '{:.1f}'}).applymap(highlight_scores).set_table_styles([
        {'selector': 'th', 'props': [
            ('font-size', '18px'),
            ('text-align', 'left'),
            ('background-color', '#2A9D8F'),
            ('color', '#ffffff'),
            ('padding', '12px')
        ]},
        {'selector': 'td', 'props': [('padding', '12px'), ('border-bottom', '1px solid #dddddd')]},
        {'selector': 'tr:nth-child(even)', 'props': [('background-color', '#f3f3f3')]},
    ]).set_table_attributes('class="styled-table"')

    st.write(styled_scores.to_html(), unsafe_allow_html=True)
else:
    st.write("Click the **Calculate Risk Score** button to see the results.")
