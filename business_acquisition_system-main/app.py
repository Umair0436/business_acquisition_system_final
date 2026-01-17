import streamlit as st
import pandas as pd
import subprocess
import sys
import os
from pathlib import Path
import shutil
from datetime import datetime
import re
import threading
import time

# Page configuration
st.set_page_config(
    page_title="Business Acquisition System",
    page_icon="🏢",
    layout="wide"
)

# Initialize session state
if 'pipeline_running' not in st.session_state:
    st.session_state.pipeline_running = False
if 'agent_status' not in st.session_state:
    st.session_state.agent_status = {
        'agent_1': 'pending',  # pending, processing, completed, failed
        'agent_2': 'pending',
        'agent_3': 'pending',
        'agent_4': 'pending'
    }
if 'logs' not in st.session_state:
    st.session_state.logs = []
if 'pipeline_step' not in st.session_state:
    st.session_state.pipeline_step = 0  # 0=not started, 1-4=agent number, 5=done
if 'pipeline_params' not in st.session_state:
    st.session_state.pipeline_params = None
if 'current_agent_input' not in st.session_state:
    st.session_state.current_agent_input = None

def log(message):
    """Add message to logs"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.logs.append(f"[{timestamp}] {message}")

def update_agent_status(agent_num, status):
    """Update agent status"""
    st.session_state.agent_status[f'agent_{agent_num}'] = status

def run_agent(agent_num, cwd, description, input_text=None, skip_status_update=False):
    """Run an agent and return success status"""
    try:
        if not skip_status_update:
            update_agent_status(agent_num, 'processing')
        log(f"🚀 Starting {description}")
        
        # Set environment to use UTF-8 encoding
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUTF8'] = '1'
        
        # Use -X utf8 flag for Python 3.7+ to force UTF-8 mode
        python_cmd = [sys.executable, "-X", "utf8", "main.py"]
        
        result = subprocess.run(
            python_cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=600,
            input=input_text,
            env=env
        )
        if result.returncode == 0:
            update_agent_status(agent_num, 'completed')
            log(f"✅ {description} completed")
            if result.stdout:
                log(f"Output: {result.stdout[:500]}")
            return True
        else:
            update_agent_status(agent_num, 'failed')
            error_msg = result.stderr if result.stderr else result.stdout
            log(f"❌ {description} failed")
            if error_msg:
                # Show more of the error
                log(f"Error details: {error_msg[:1000]}")
            return False
    except Exception as e:
        update_agent_status(agent_num, 'failed')
        log(f"❌ {description} error: {str(e)}")
        return False

def copy_file(source, dest):
    """Copy file from source to destination"""
    try:
        source_path = Path(source)
        dest_path = Path(dest)
        if source_path.exists():
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(source_path, dest_path)
            log(f"✓ Copied {source_path.name}")
            return True
        else:
            log(f"⚠ {source_path.name} not found")
            return False
    except Exception as e:
        log(f"❌ Copy error: {str(e)}")
        return False

def update_agent1_config(num_listings):
    """Update Agent 1 config with number of listings"""
    try:
        config_path = Path("agent_1/config.py")
        if config_path.exists():
            config_content = config_path.read_text()
            config_content = re.sub(
                r'"max_listings":\s*\d+',
                f'"max_listings": {num_listings}',
                config_content
            )
            config_path.write_text(config_content)
            log(f"✓ Updated config: {num_listings} listings per website")
            return True
        return False
    except Exception as e:
        log(f"⚠ Config update warning: {str(e)}")
        return False

def run_pipeline(num_listings=5, email_tone='professional'):
    """Run the complete pipeline sequentially"""
    st.session_state.logs = []
    st.session_state.pipeline_running = True
    
    # Reset all agent statuses
    for i in range(1, 5):
        update_agent_status(i, 'pending')
    
    # Update Agent 1 config
    update_agent1_config(num_listings)
    
    # Agent 1: Scraping (needs input for number of listings)
    agent1_input = f"{num_listings}\n"
    if not run_agent(1, "agent_1", "Agent 1: Business Listing Scraper", input_text=agent1_input):
        st.session_state.pipeline_running = False
        return False
    
    time.sleep(1)  # Small delay for UI update
    
    # Copy Agent 1 output to Agent 2
    copy_file("agent_1/output/listings.csv", "agent_2/input/listings.csv")
    
    # Agent 2: Broker Intelligence
    if not run_agent(2, "agent_2", "Agent 2: Broker Intelligence"):
        st.session_state.pipeline_running = False
        return False
    
    time.sleep(1)  # Small delay for UI update
    
    # Copy Agent 2 output to Agent 3
    copy_file("agent_2/output/Master_Broker_Database.csv", "agent_3/input/Master_Broker_Database.csv")
    
    # Agent 3: Email Outreach
    tone_map = {'professional': 'p', 'relationship': 'r', 'direct': 'd'}
    tone_input = tone_map.get(email_tone, 'p')
    if not run_agent(3, "agent_3", "Agent 3: Email Outreach", input_text=f"{tone_input}\n"):
        st.session_state.pipeline_running = False
        return False
    
    time.sleep(1)  # Small delay for UI update
    
    # Copy all files to Agent 4
    copy_file("agent_1/output/listings.csv", "agent_4/input/listings.csv")
    copy_file("agent_2/output/Master_Broker_Database.csv", "agent_4/input/Master_Broker_Database.csv")
    copy_file("agent_3/output/email_drafts.csv", "agent_4/input/email_drafts.csv")
    
    # Agent 4: Data Catalog
    if not run_agent(4, "agent_4", "Agent 4: Data Catalog"):
        st.session_state.pipeline_running = False
        return False
    
    time.sleep(1)  # Small delay for UI update
    
    log("🎉 Pipeline completed successfully!")
    st.session_state.pipeline_running = False
    return True

def get_output_files():
    """Get list of available output files"""
    files = {}
    outputs = {
        "Business Listings": "agent_1/output/listings.csv",
        "Broker Database": "agent_2/output/Master_Broker_Database.csv",
        "Email Drafts": "agent_3/output/email_drafts.csv"
    }
    for name, path in outputs.items():
        if Path(path).exists():
            files[name] = path
    return files

def get_status_color(status):
    """Get color based on status"""
    colors = {
        'pending': '#E0E0E0',      # Gray
        'processing': '#FFA500',   # Orange
        'completed': '#4CAF50',    # Green
        'failed': '#F44336'        # Red
    }
    return colors.get(status, '#E0E0E0')

def get_status_text(status):
    """Get text based on status"""
    texts = {
        'pending': 'Pending',
        'processing': 'Processing...',
        'completed': 'Completed',
        'failed': 'Failed'
    }
    return texts.get(status, 'Pending')

# Main UI
st.title("🏢 Business Acquisition System")
st.markdown("---")

# Create layout: Left (controls), Center (agents), Right (downloads)
left_col, center_col, right_col = st.columns([1.5, 3, 2])

with left_col:
    st.header("⚙️ Configuration")
    
    # Number input for listings
    num_listings = st.number_input(
        "Number of listings per website",
        min_value=1,
        max_value=50,
        value=5,
        help="Kitni listings har website se scrape karni hain"
    )
    
    st.markdown("---")
    
    # Dropdown for email tone
    email_tone = st.selectbox(
        "Email Tone",
        ["professional", "relationship", "direct"],
        index=0,
        help="Email ka tone select karein"
    )
    
    st.markdown("---")
    
    # Start Pipeline Button
    if st.button("🚀 Start Pipeline", type="primary", use_container_width=True, disabled=st.session_state.pipeline_running):
        st.session_state.pipeline_running = True
        st.session_state.pipeline_step = 0
        st.session_state.logs = []
        st.session_state.pipeline_params = (int(num_listings), email_tone)
        # Reset agent statuses
        for i in range(1, 5):
            update_agent_status(i, 'pending')
        # Initialize pipeline
        update_agent1_config(int(num_listings))
        st.session_state.pipeline_step = 1  # Start with Agent 1
        st.rerun()

with right_col:
    # Download Files Section
    st.header("📥 Download Files")
    output_files = get_output_files()
    
    if output_files:
        for name, path in output_files.items():
            if Path(path).exists():
                try:
                    file_path = Path(path)
                    if file_path.stat().st_size > 0:
                        file_size = file_path.stat().st_size
                        
                        # Read file data with error handling
                        try:
                            with open(file_path, 'rb') as f:
                                file_data = f.read()
                            
                            # Create download button
                            st.download_button(
                                label=f"📄 {name} ({file_size // 1024} KB)",
                                data=file_data,
                                file_name=file_path.name,
                                mime="text/csv",
                                use_container_width=True,
                                key=f"download_{name}_{file_path.stat().st_mtime}"
                            )
                        except IOError as e:
                            st.warning(f"⚠️ {name}: File is being used by another process")
                        except Exception as e:
                            st.error(f"Error reading {name}: {str(e)}")
                    else:
                        st.info(f"⏳ {name}: File is empty")
                except Exception as e:
                    st.error(f"Error accessing {name}: {str(e)}")
    else:
        st.info("⏳ No files available yet. Run pipeline to generate files.")

with center_col:
    st.header("🤖 Agents Status")
    
    # Agent Cards in 2x2 grid
    agents_info = [
        (1, "Agent 1", "Business Listing Scraper"),
        (2, "Agent 2", "Broker Intelligence"),
        (3, "Agent 3", "Email Outreach"),
        (4, "Agent 4", "Data Catalog")
    ]
    
    # Create 2x2 grid
    col1, col2 = st.columns(2)
    
    with col1:
        # Agent 1
        agent_num, agent_name, agent_desc = agents_info[0]
        status = st.session_state.agent_status[f'agent_{agent_num}']
        color = get_status_color(status)
        status_text = get_status_text(status)
        st.markdown(f"""
        <div style="
            background-color: {color};
            padding: 10px;
            border-radius: 8px;
            margin: 5px 0;
            text-align: center;
            border: 2px solid #333;
        ">
            <h3 style="margin: 0; color: #333; font-size: 18px;">{agent_desc}</h3>
            <h4 style="margin: 5px 0; color: #333; font-size: 16px;">{status_text}</h4>
        </div>
        """, unsafe_allow_html=True)
        
        # Agent 3
        agent_num, agent_name, agent_desc = agents_info[2]
        status = st.session_state.agent_status[f'agent_{agent_num}']
        color = get_status_color(status)
        status_text = get_status_text(status)
        st.markdown(f"""
        <div style="
            background-color: {color};
            padding: 10px;
            border-radius: 8px;
            margin: 5px 0;
            text-align: center;
            border: 2px solid #333;
        ">
            <h3 style="margin: 0; color: #333; font-size: 18px;">{agent_desc}</h3>
            <h4 style="margin: 5px 0; color: #333; font-size: 16px;">{status_text}</h4>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # Agent 2
        agent_num, agent_name, agent_desc = agents_info[1]
        status = st.session_state.agent_status[f'agent_{agent_num}']
        color = get_status_color(status)
        status_text = get_status_text(status)
        st.markdown(f"""
        <div style="
            background-color: {color};
            padding: 10px;
            border-radius: 8px;
            margin: 5px 0;
            text-align: center;
            border: 2px solid #333;
        ">
            <h3 style="margin: 0; color: #333; font-size: 18px;">{agent_desc}</h3>
            <h4 style="margin: 5px 0; color: #333; font-size: 16px;">{status_text}</h4>
        </div>
        """, unsafe_allow_html=True)
        
        # Agent 4
        agent_num, agent_name, agent_desc = agents_info[3]
        status = st.session_state.agent_status[f'agent_{agent_num}']
        color = get_status_color(status)
        status_text = get_status_text(status)
        st.markdown(f"""
        <div style="
            background-color: {color};
            padding: 10px;
            border-radius: 8px;
            margin: 5px 0;
            text-align: center;
            border: 2px solid #333;
        ">
            <h3 style="margin: 0; color: #333; font-size: 18px;">{agent_desc}</h3>
            <h4 style="margin: 5px 0; color: #333; font-size: 16px;">{status_text}</h4>
        </div>
        """, unsafe_allow_html=True)
    
    # Pipeline Status
    if st.session_state.pipeline_running:
        st.info("🔄 Pipeline is running...")
    elif all(st.session_state.agent_status[f'agent_{i}'] == 'completed' for i in range(1, 5)):
        st.success("✅ All agents completed successfully!")
    
    # Logs Section
    if st.session_state.logs:
        with st.expander("📝 Execution Logs", expanded=False):
            log_text = "\n".join(st.session_state.logs[-30:])
            st.text_area("", log_text, height=200, disabled=True, label_visibility="collapsed")


# Execute pipeline step by step
if st.session_state.pipeline_running and st.session_state.pipeline_params:
    num_listings, email_tone = st.session_state.pipeline_params
    step = st.session_state.pipeline_step
    
    if step == 1:
        # Set status to processing first, then run Agent 1
        update_agent_status(1, 'processing')
        st.session_state.pipeline_step = 1.1
        st.rerun()
    
    elif step == 1.1:  # Agent 1 execution
        agent1_input = f"{num_listings}\n"
        if run_agent(1, "agent_1", "Agent 1: Business Listing Scraper", input_text=agent1_input, skip_status_update=True):
            copy_file("agent_1/output/listings.csv", "agent_2/input/listings.csv")
            st.session_state.pipeline_step = 2
            st.rerun()
        else:
            st.session_state.pipeline_running = False
    
    elif step == 2:
        # Set status to processing first, then run Agent 2
        update_agent_status(2, 'processing')
        st.session_state.pipeline_step = 2.1
        st.rerun()
    
    elif step == 2.1:  # Agent 2 execution
        if run_agent(2, "agent_2", "Agent 2: Broker Intelligence", skip_status_update=True):
            copy_file("agent_2/output/Master_Broker_Database.csv", "agent_3/input/Master_Broker_Database.csv")
            st.session_state.pipeline_step = 3
            st.rerun()
        else:
            st.session_state.pipeline_running = False
    
    elif step == 3:
        # Set status to processing first, then run Agent 3
        update_agent_status(3, 'processing')
        st.session_state.pipeline_step = 3.1
        st.rerun()
    
    elif step == 3.1:  # Agent 3 execution
        tone_map = {'professional': 'p', 'relationship': 'r', 'direct': 'd'}
        tone_input = tone_map.get(email_tone, 'p')
        if run_agent(3, "agent_3", "Agent 3: Email Outreach", input_text=f"{tone_input}\n", skip_status_update=True):
            copy_file("agent_1/output/listings.csv", "agent_4/input/listings.csv")
            copy_file("agent_2/output/Master_Broker_Database.csv", "agent_4/input/Master_Broker_Database.csv")
            copy_file("agent_3/output/email_drafts.csv", "agent_4/input/email_drafts.csv")
            st.session_state.pipeline_step = 4
            st.rerun()
        else:
            st.session_state.pipeline_running = False
    
    elif step == 4:
        # Set status to processing first, then run Agent 4
        update_agent_status(4, 'processing')
        st.session_state.pipeline_step = 4.1
        st.rerun()
    
    elif step == 4.1:  # Agent 4 execution
        if run_agent(4, "agent_4", "Agent 4: Data Catalog", skip_status_update=True):
            log("🎉 Pipeline completed successfully!")
            st.session_state.pipeline_step = 5
            st.session_state.pipeline_running = False
            st.rerun()
        else:
            st.session_state.pipeline_running = False

# Footer
st.markdown("---")
st.markdown("**Business Acquisition System** - Multi-Agent Pipeline")
