import streamlit as st
import pandas as pd
import io
import time
from scraper_backend import scrape_google_maps

# Set Streamlit Page Configuration
st.set_page_config(
    page_title="MapScraper - Local B2B Lead Generator",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium Sleek CSS Styling for a High-End UX
st.markdown("""
<style>
    /* Google Font Import */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=Outfit:wght@400;600;800&display=swap');
    
    /* Core Layout & Font Overrides */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .stTitle h1 {
        font-family: 'Outfit', sans-serif;
        background: linear-gradient(135deg, #FF6B6B 0%, #FF8E53 50%, #4D96FF 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 3rem !important;
        margin-bottom: 0.5rem !important;
    }
    
    /* Custom Card Styling */
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        transition: all 0.3s ease;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        border-color: rgba(77, 150, 255, 0.4);
        box-shadow: 0 10px 30px rgba(77, 150, 255, 0.1);
    }
    
    .metric-value {
        font-size: 2.2rem;
        font-weight: 700;
        color: #4D96FF;
        margin-bottom: 5px;
    }
    
    .metric-label {
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: #B2B2B2;
    }
    
    /* Log Box */
    .log-box {
        background-color: #0E1117;
        border: 1px solid #262730;
        border-radius: 8px;
        padding: 15px;
        font-family: 'Courier New', Courier, monospace;
        height: 250px;
        overflow-y: scroll;
        color: #00FF66;
        margin-bottom: 20px;
    }
    
    /* Footer */
    .footer-text {
        text-align: center;
        color: #5F6368;
        font-size: 0.85rem;
        margin-top: 50px;
    }
</style>
""", unsafe_allow_html=True)

# Application Header & Hero Banner
import os

# Application Header & Hero Banner
col_title, col_logo = st.columns([4, 1])
with col_title:
    st.title("🗺️ MapScraper Pro")
    st.caption("Local, Privacy-Focused Google Maps B2B Lead Generator — 100% Free & Unlimited")
with col_logo:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(script_dir, "logo1.png")
    if os.path.exists(logo_path):
        st.image(logo_path, use_container_width=True)
    else:
        st.markdown("<br>", unsafe_allow_html=True)
        st.write("")

st.divider()

# Sidebar: Controls & Enrichment Options
with st.sidebar:
    st.header("⚙️ Configuration")
    st.markdown("Specify your target profile and filters.")
    
    keyword = st.text_input("💼 Keyword / Business Type", placeholder="e.g. Bakery, Dentist, CPA")
    
    st.markdown("---")
    st.subheader("📍 Geolocation")
    state = st.text_input("🇺🇸 State / Province", placeholder="e.g. Texas or NSW", value="")
    country = st.text_input("🌍 Country", value="USA")
    
    st.markdown("---")
    st.subheader("🎯 Extraction Limits")
    limit = st.number_input("Limit per City", min_value=1, max_value=500, value=10, step=5,
                            help="Max number of matching business listings to scrape per city.")
    
    st.markdown("---")
    st.subheader("🛡️ Filters & Enrichment")
    phone_only = st.checkbox("Require Phone Number", value=False, help="Filter out businesses without registered phone numbers.")
    website_only = st.checkbox("Require Website Link", value=False, help="Filter out businesses without website listings.")
    email_enrich = st.checkbox("Enrich Email Address 📧", value=True, 
                              help="If a website is found, crawl the homepage to extract contact email addresses.")
    
    st.markdown("---")
    start_btn = st.button("🔥 Start Lead Generation Campaign", use_container_width=True, type="primary")

# Main Layout
tab1, tab2 = st.tabs(["🚀 Lead Extraction", "📚 How to Use & Privacy"])

with tab1:
    col_input, col_info = st.columns([3, 2])
    
    with col_input:
        st.subheader("🏙️ Target Cities Selection")
        city_input_method = st.radio(
            "Select City Input Method",
            ["Comma-separated list", "Upload TXT File"],
            horizontal=True
        )
        
        cities = []
        if city_input_method == "Comma-separated list":
            cities_text = st.text_area(
                "Enter Cities",
                placeholder="Austin, Dallas, Houston, San Antonio",
                help="Enter list of cities separated by commas."
            )
            if cities_text:
                cities = [c.strip() for c in cities_text.split(",") if c.strip()]
        else:
            uploaded_file = st.file_uploader("Upload Cities TXT File (one city per line)", type=["txt"])
            if uploaded_file is not None:
                stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8"))
                cities = [line.strip() for line in stringio if line.strip()]
                st.success(f"Loaded {len(cities)} cities from uploaded file.")
                
    with col_info:
        st.subheader("📊 Extraction Summary")
        if keyword and cities:
            st.info(f"""
            - **Campaign:** Google Maps Scraping
            - **Target:** `{keyword}`
            - **Cities Count:** `{len(cities)}` cities
            - **Total Scan Target:** Up to `{len(cities) * limit}` potential listings
            - **Requirements:** Phone: `{"Yes" if phone_only else "No"}` | Website: `{"Yes" if website_only else "No"}` | Emails: `{"Yes" if email_enrich else "No"}`
            """)
        else:
            st.warning("Please configure **Keyword** in the sidebar and enter/upload **Cities** to get started.")

    st.markdown("<br>", unsafe_allow_html=True)
    
    # Session State Initialization
    if "leads_df" not in st.session_state:
        st.session_state.leads_df = pd.DataFrame()
    if "log_text" not in st.session_state:
        st.session_state.log_text = ""
        
    # Campaign is initiated via the sidebar menu button
    
    if start_btn:
        # Input Validation
        if not keyword:
            st.error("❌ Please provide a Target Keyword in the sidebar.")
        elif len(cities) == 0:
            st.error("❌ Please input or upload at least one target city.")
        else:
            st.session_state.leads_df = pd.DataFrame() # Reset session data
            st.session_state.log_text = "Starting campaigns...\n"
            
            # Interactive Progress Widgets
            global_progress_bar = st.progress(0)
            city_progress_text = st.empty()
            scraper_log_box = st.empty()
            
            # Initialize intermediate list and state backup variable if not exists
            scraped_items_list = []
            if "backup_leads" not in st.session_state:
                st.session_state.backup_leads = []
            st.session_state.backup_leads = [] # Reset backup
            
            total_cities = len(cities)
            for idx, current_city in enumerate(cities):
                city_percentage = int(((idx) / total_cities) * 100)
                global_progress_bar.progress(city_percentage)
                city_progress_text.markdown(f"### 🏙️ Processing City: **{current_city}** ({idx + 1}/{total_cities})")
                
                # Append to logs
                st.session_state.log_text += f"\n--- Initiating Scrape: '{keyword}' in {current_city} ---\n"
                scraper_log_box.code(st.session_state.log_text, language="bash")
                
                # Call Scraper Generator
                try:
                    generator = scrape_google_maps(
                        keyword=keyword,
                        city=current_city,
                        state=state,
                        country=country,
                        limit=limit,
                        phone_only=phone_only,
                        website_only=website_only,
                        email_enrich=email_enrich
                    )
                    
                    # Read generator stream
                    for event in generator:
                        event_type = event.get("status")
                        
                        if event_type == "info":
                            msg = event.get("message")
                            st.session_state.log_text += f"[INFO] {msg}\n"
                            scraper_log_box.code(st.session_state.log_text, language="bash")
                            
                        elif event_type == "scroll":
                            disc = event.get("discovered")
                            lim = event.get("limit")
                            st.session_state.log_text += f"[SCROLL] Discovered {disc}/{lim} listings...\n"
                            scraper_log_box.code(st.session_state.log_text, language="bash")
                            
                        elif event_type == "progress":
                            curr = event.get("count")
                            tot = event.get("total")
                            biz = event.get("business")
                            name = biz.get("name", "Unknown")
                            st.session_state.log_text += f"[SUCCESS] Scraped [{curr}/{tot}]: {name}\n"
                            scraper_log_box.code(st.session_state.log_text, language="bash")
                            
                        elif event_type == "error":
                            err = event.get("message")
                            st.session_state.log_text += f"[ERROR] {err}\n"
                            scraper_log_box.code(st.session_state.log_text, language="bash")
                            
                        elif event_type == "done":
                            city_results = event.get("results", [])
                            st.session_state.log_text += f"[CITY DONE] Scraped {len(city_results)} valid leads in {current_city}.\n"
                            scraper_log_box.code(st.session_state.log_text, language="bash")
                            scraped_items_list.extend(city_results)
                            
                            # Failsafe Backup: Save current intermediate results in a backup state DataFrame
                            if scraped_items_list:
                                backup_df = pd.DataFrame(scraped_items_list)
                                # Safely clean duplicates for intermediate backup
                                backup_df['name_clean'] = backup_df['name'].fillna('').str.strip().str.lower()
                                backup_df['address_clean'] = backup_df['address'].fillna('').str.strip().str.lower()
                                clean_backup_df = backup_df.drop_duplicates(subset=['name_clean', 'address_clean'], keep='first')
                                clean_backup_df = clean_backup_df.drop(columns=['name_clean', 'address_clean'])
                                
                                st.session_state.backup_leads = clean_backup_df.to_dict('records')
                                st.session_state.leads_df = clean_backup_df.reset_index(drop=True)
                            
                except Exception as ex:
                    st.session_state.log_text += f"[CRITICAL ERROR] City {current_city} failed: {ex}\n"
                    scraper_log_box.code(st.session_state.log_text, language="bash")
                    
            # Complete Progress
            global_progress_bar.progress(100)
            city_progress_text.markdown("### 🎉 Campaign Execution Completed!")
            st.session_state.log_text += "\n--- Finalizing and deduplicating unified records ---\n"
            scraper_log_box.code(st.session_state.log_text, language="bash")
            
            # Populate Dataframe and Deduplicate
            if scraped_items_list:
                raw_df = pd.DataFrame(scraped_items_list)
                
                # Deduplication using Title and Address to handle edge overlaps safely
                # Fill NAs to avoid drop_duplicates matching nulls incorrectly
                raw_df['name_clean'] = raw_df['name'].fillna('').str.strip().str.lower()
                raw_df['address_clean'] = raw_df['address'].fillna('').str.strip().str.lower()
                
                dedup_df = raw_df.drop_duplicates(subset=['name_clean', 'address_clean'], keep='first')
                # Clean up temp columns
                dedup_df = dedup_df.drop(columns=['name_clean', 'address_clean'])
                
                st.session_state.leads_df = dedup_df.reset_index(drop=True)
                st.session_state.backup_leads = dedup_df.to_dict('records') # Update backup to final
                st.success(f"Successfully processed leads. Discovered {len(raw_df)} listings. Unique Leads: {len(st.session_state.leads_df)}")
            else:
                # Try fallback to whatever was backed up in session state
                if "backup_leads" in st.session_state and st.session_state.backup_leads:
                    st.session_state.leads_df = pd.DataFrame(st.session_state.backup_leads)
                    st.warning("Scrape loop finished with issues, but recovered intermediate scraped results from backup.")
                else:
                    st.session_state.leads_df = pd.DataFrame()
                    st.warning("No listings matched your criteria in the requested cities.")
                
    # Dashboard KPI Cards & Data Presentation
    if not st.session_state.leads_df.empty:
        df = st.session_state.leads_df
        
        # Calculate Stats
        total_leads = len(df)
        phone_count = df['phone'].astype(str).str.strip().ne('').sum()
        website_count = df['website'].astype(str).str.strip().ne('').sum()
        email_count = df['email'].astype(str).str.strip().ne('').sum() if 'email' in df.columns else 0
        
        st.markdown("### 📊 Live Campaign Metrics")
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        
        with col_m1:
            st.markdown(f'<div class="metric-card"><div class="metric-value">{total_leads}</div><div class="metric-label">Total Unique Leads</div></div>', unsafe_allow_html=True)
        with col_m2:
            st.markdown(f'<div class="metric-card"><div class="metric-value">{phone_count}</div><div class="metric-label">With Phone Numbers</div></div>', unsafe_allow_html=True)
        with col_m3:
            st.markdown(f'<div class="metric-card"><div class="metric-value">{website_count}</div><div class="metric-label">With Website Link</div></div>', unsafe_allow_html=True)
        with col_m4:
            st.markdown(f'<div class="metric-card"><div class="metric-value">{email_count}</div><div class="metric-label">With Emails Enriched</div></div>', unsafe_allow_html=True)
            
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 📋 Generated Leads Database")
        
        # Display Interactive Dataframe
        st.dataframe(df, use_container_width=True)
        
        # Export Option
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_data = csv_buffer.getvalue()
        
        st.download_button(
            label="📥 Download Extracted Leads as CSV",
            data=csv_data,
            file_name=f"google_maps_leads_{keyword.lower().replace(' ', '_')}.csv",
            mime="text/csv",
            use_container_width=True
        )

with tab2:
    st.subheader("📖 Application Overview")
    st.write("""
    **MapScraper Pro** is a privacy-first lead extraction software that lets you generate highly targeted B2B contact lists.
    Because it runs completely on your local computer using your local browser automation, it is **100% private, free, and does not require expensive subscription APIs**.
    """)
    
    st.markdown("### 🛠️ Step-by-Step Instructions")
    st.info("""
    1. **Fill in Keyword**: Enter what business type you want (e.g. *Digital Marketing Agency*, *Plumbers*, *Gyms*).
    2. **State & Country**: Keep it accurate to assist Google Maps geolocation search.
    3. **Set limit per city**: 10–20 is perfect for testing. Scale up as required.
    4. **Enrichment**: Select whether to automatically scrape websites for business email addresses.
    5. **Input Cities**: Enter multiple target cities (either separated by commas or upload a `.txt` file with one city per line).
    6. **Start Campaign**: Click the large button to start. Monitor the automated Selenium actions in real time via the logging dashboard!
    7. **Download CSV**: Once complete, inspect details on the interactive dashboard and export a clean spreadsheet immediately.
    """)
    
    st.markdown("### 🔒 Privacy First Architecture")
    st.success("""
    - **Zero Data Leakage**: Your keywords, target cities, and downloaded lead data are stored locally in your RAM and exported to your own filesystem. No external third-party server has access to your search history.
    - **No Google Maps API Key Needed**: MapScraper uses intelligent Selenium browser simulation to search maps natively, saving you hundreds of dollars in API call fees.
    - **Gentle Crawler Configuration**: The application incorporates built-in wait delays between pages and steps to stay undetected and comply with standard browser limits.
    """)

st.markdown('<div class="footer-text">MapScraper Pro v1.0.0 • Built for High Performance B2B Lead Generation</div>', unsafe_allow_html=True)
