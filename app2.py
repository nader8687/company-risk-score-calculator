import streamlit as st
import pandas as pd
import numpy as np
import re
from joblib import Parallel, delayed
import time


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
        cancellation_ratio = visa_cancelled / total_visas
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
    if wps_status in ['PRIVATE', 'private', 'N', 'N/', 'N/A', 'NA', '']:
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


# Load only required columns from the Excel and CSV files
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


def calculate_risk_score(row, weights):
    scores = {}
    scores['Economic Zone'] = calculate_economic_zone_score(row['economic_department']) * weights['Economic Zone']
    scores['Date of Operations'] = calculate_date_of_operations_score(row['est_date'], row['expiry_date']) * weights[
        'Date of Operations']
    scores['Status'] = calculate_status_score(row['status']) * weights['Status']
    scores['Legal Type'] = calculate_legal_type_score(row['legal_type']) * weights['Legal Type']
    scores['WPS'] = calculate_wps_score(row['wps']) * weights['WPS']
    scores['Visa Number'] = calculate_visa_number_score(row['visa_approved'], row['visa_cancelled']) * weights[
        'Visa Number']
    scores['Visa Ratio'] = calculate_visa_ratio_score(row['visa_approved'], row['visa_cancelled'],
                                                      row['visa_requested'], row['visa_used']) * weights['Visa Ratio']
    scores['Phone'] = calculate_phone_score(row['phone_no'] if pd.notnull(row['phone_no']) else row['mobile_no']) * \
                      weights['Phone']
    scores['Website'] = calculate_website_score(row['website_url']) * weights['Website']
    scores['Email'] = calculate_email_score(row['email']) * weights['Email']
    scores['Branch'] = calculate_branch_score(row['is_branch']) * weights['Branch']
    scores['Total'] = sum(scores.values())
    return scores


# Streamlit application
st.set_page_config(page_title="Company Risk Score Calculator", layout="wide")
st.title("📊 Company Risk Score Calculator")

# Sidebar for inputs
st.sidebar.header("Company Selection and Feature Weights")

# User selects features for the company
selected_company_name = st.sidebar.selectbox("Select Business Name:", df['business_name_english'].unique())

# Populate features based on selected company
selected_company = df[df['business_name_english'] == selected_company_name].iloc[0]

# User inputs and modifications for the selected company features
st.sidebar.subheader("Company Details")
features = {}
for column in ['economic_department', 'status', 'legal_type', 'wps', 'is_branch']:
    features[column] = st.sidebar.selectbox(f"{column.replace('_', ' ').title()}:", df[column].unique(),
                                            index=df[column].tolist().index(selected_company[column]))

for column in ['visa_approved', 'visa_cancelled', 'visa_requested', 'visa_used']:
    features[column] = st.sidebar.number_input(f"Enter {column.replace('_', ' ').title()}:",
                                               value=int(selected_company[column]))

for column in ['phone_no', 'mobile_no', 'website_url', 'email']:
    placeholder = f"Enter {column.replace('_', ' ').title()} (e.g., +971-50-123-4567):" if column in ['phone_no',
                                                                                                      'mobile_no'] else f"Enter {column.replace('_', ' ').title()}:"
    features[column] = st.sidebar.text_input(placeholder, value=str(selected_company[column]))

features['est_date'] = st.sidebar.date_input("Select Establishment Date:",
                                             value=pd.to_datetime(selected_company['est_date']))
features['expiry_date'] = st.sidebar.date_input("Select Expiry Date:",
                                                value=pd.to_datetime(selected_company['expiry_date']))

# User selects weights for each feature with default values
st.sidebar.subheader("Feature Weights")
weights = {
    'Economic Zone': st.sidebar.slider("Weight for Economic Zone:", 0.0, 1.0, 0.15),
    'Date of Operations': st.sidebar.slider("Weight for Date of Operations:", 0.0, 1.0, 0.30),
    'Status': st.sidebar.slider("Weight for Status:", 0.0, 1.0, 0.10),
    'Legal Type': st.sidebar.slider("Weight for Legal Type:", 0.0, 1.0, 0.10),
    'WPS': st.sidebar.slider("Weight for WPS:", 0.0, 1.0, 0.05),
    'Visa Number': st.sidebar.slider("Weight for Visa Number:", 0.0, 1.0, 0.30),
    'Visa Ratio': st.sidebar.slider("Weight for Visa Ratio:", 0.0, 1.0, 0.30),
    'Phone': st.sidebar.slider("Weight for Phone:", 0.0, 1.0, 0.10),
    'Website': st.sidebar.slider("Weight for Website:", 0.0, 1.0, 0.10),
    'Email': st.sidebar.slider("Weight for Email:", 0.0, 1.0, 0.10),
    'Branch': st.sidebar.slider("Weight for Branch:", 0.0, 1.0, 0.10)
}

# Layout for main content
st.markdown("## Company Details and Risk Score Calculation")
st.markdown("### Selected Company Information")

with st.expander("See Selected Company Details"):
    st.write(selected_company)

# Calculate risk score for the selected features
if st.button("Calculate Risk Score"):
    risk_scores = calculate_risk_score(features, weights)
    st.markdown("### Risk Scores")
    st.write(risk_scores)
    st.markdown(f"**Total Risk Score:** {risk_scores['Total']}")
