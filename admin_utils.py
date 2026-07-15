import streamlit as st

def parse_bool(val):
    if isinstance(val, bool): return val
    return str(val).strip().lower() in ['true', '1', 't', 'y', 'yes']

def get_premium_header(icon, title, color="#1E3A8A"):
    gradient = f"linear-gradient(135deg, {color}E6 0%, #2563EB 100%)"
    
    html = f"""
    <div style='display: flex; align-items: center; margin-top: 15px; margin-bottom: 25px; padding-bottom: 15px; border-bottom: 2px solid #e2e8f0;'>
        <div style='background: {gradient}; color: white; width: 42px; height: 42px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 22px; margin-right: 15px; box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);'>
            {icon}
        </div>
        <h3 style='margin: 0; color: #0f172a; font-size: 24px; font-weight: 800; letter-spacing: -0.5px;'>
            {title}
        </h3>
    </div>
    """
    return html
