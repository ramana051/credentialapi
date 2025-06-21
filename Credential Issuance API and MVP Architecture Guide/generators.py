"""
PDF and PNG generation utilities for credentials.
"""

from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from PIL import Image as PILImage, ImageDraw, ImageFont
from io import BytesIO
import base64
import os
from typing import Dict, Any, Optional
from datetime import datetime

from shared.utils import generate_qr_code


class CredentialGenerator:
    """Generate credential files (PDF and PNG) from templates."""
    
    def __init__(self, upload_directory: str = "/app/uploads"):
        self.upload_directory = upload_directory
        self.credentials_dir = os.path.join(upload_directory, "credentials")
        self.qr_codes_dir = os.path.join(upload_directory, "qr_codes")
        
        # Ensure directories exist
        os.makedirs(self.credentials_dir, exist_ok=True)
        os.makedirs(self.qr_codes_dir, exist_ok=True)
    
    def generate_pdf(
        self,
        credential_data: Dict[str, Any],
        template_design: Dict[str, Any],
        output_path: str
    ) -> str:
        """Generate PDF credential."""
        
        # Create PDF document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Build content
        story = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#2563EB')
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontSize=18,
            spaceAfter=20,
            alignment=TA_CENTER
        )
        
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=12,
            alignment=TA_CENTER
        )
        
        # Add organization logo if available
        if template_design.get('logo_url'):
            try:
                logo = Image(template_design['logo_url'], width=2*inch, height=1*inch)
                logo.hAlign = 'CENTER'
                story.append(logo)
                story.append(Spacer(1, 20))
            except:
                pass  # Skip if logo can't be loaded
        
        # Certificate title
        story.append(Paragraph("CERTIFICATE OF ACHIEVEMENT", title_style))
        story.append(Spacer(1, 20))
        
        # Credential title
        story.append(Paragraph(credential_data['title'], subtitle_style))
        story.append(Spacer(1, 30))
        
        # Recipient information
        story.append(Paragraph("This is to certify that", body_style))
        story.append(Spacer(1, 10))
        
        recipient_style = ParagraphStyle(
            'RecipientName',
            parent=styles['Normal'],
            fontSize=20,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1F2937'),
            fontName='Helvetica-Bold'
        )
        
        story.append(Paragraph(credential_data['recipient_name'], recipient_style))
        story.append(Spacer(1, 20))
        
        # Description
        if credential_data.get('description'):
            story.append(Paragraph(credential_data['description'], body_style))
            story.append(Spacer(1, 30))
        
        # Issue date and expiration
        date_info = []
        if credential_data.get('issued_at'):
            issue_date = datetime.fromisoformat(credential_data['issued_at'].replace('Z', '+00:00'))
            date_info.append(f"Issued on: {issue_date.strftime('%B %d, %Y')}")
        
        if credential_data.get('expires_at'):
            exp_date = datetime.fromisoformat(credential_data['expires_at'].replace('Z', '+00:00'))
            date_info.append(f"Expires on: {exp_date.strftime('%B %d, %Y')}")
        
        if date_info:
            story.append(Paragraph(" | ".join(date_info), body_style))
            story.append(Spacer(1, 30))
        
        # Credential ID and verification
        story.append(Paragraph(f"Credential ID: {credential_data['credential_id']}", body_style))
        story.append(Spacer(1, 10))
        
        if credential_data.get('verification_url'):
            story.append(Paragraph(f"Verify at: {credential_data['verification_url']}", body_style))
            story.append(Spacer(1, 20))
            
            # Add QR code
            qr_code_data = generate_qr_code(credential_data['verification_url'], size=150)
            if qr_code_data.startswith('data:image/png;base64,'):
                qr_image_data = base64.b64decode(qr_code_data.split(',')[1])
                qr_image = ImageReader(BytesIO(qr_image_data))
                qr_img = Image(qr_image, width=1.5*inch, height=1.5*inch)
                qr_img.hAlign = 'CENTER'
                story.append(qr_img)
        
        # Build PDF
        doc.build(story)
        return output_path
    
    def generate_png(
        self,
        credential_data: Dict[str, Any],
        template_design: Dict[str, Any],
        output_path: str
    ) -> str:
        """Generate PNG credential."""
        
        # Create image
        width, height = 1200, 800
        img = PILImage.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)
        
        # Load fonts (fallback to default if not available)
        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
            subtitle_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
            body_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
            small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        except:
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
            body_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # Colors
        primary_color = template_design.get('primary_color', '#2563EB')
        text_color = '#1F2937'
        
        # Draw border
        border_width = 10
        draw.rectangle(
            [border_width, border_width, width-border_width, height-border_width],
            outline=primary_color,
            width=3
        )
        
        # Title
        title_text = "CERTIFICATE OF ACHIEVEMENT"
        title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        draw.text(
            ((width - title_width) // 2, 80),
            title_text,
            fill=primary_color,
            font=title_font
        )
        
        # Credential title
        cred_title = credential_data['title']
        cred_bbox = draw.textbbox((0, 0), cred_title, font=subtitle_font)
        cred_width = cred_bbox[2] - cred_bbox[0]
        draw.text(
            ((width - cred_width) // 2, 150),
            cred_title,
            fill=text_color,
            font=subtitle_font
        )
        
        # "This is to certify that" text
        certify_text = "This is to certify that"
        certify_bbox = draw.textbbox((0, 0), certify_text, font=body_font)
        certify_width = certify_bbox[2] - certify_bbox[0]
        draw.text(
            ((width - certify_width) // 2, 220),
            certify_text,
            fill=text_color,
            font=body_font
        )
        
        # Recipient name
        recipient_name = credential_data['recipient_name']
        recipient_bbox = draw.textbbox((0, 0), recipient_name, font=title_font)
        recipient_width = recipient_bbox[2] - recipient_bbox[0]
        draw.text(
            ((width - recipient_width) // 2, 270),
            recipient_name,
            fill=primary_color,
            font=title_font
        )
        
        # Description
        if credential_data.get('description'):
            desc_text = credential_data['description']
            # Word wrap for long descriptions
            words = desc_text.split()
            lines = []
            current_line = []
            
            for word in words:
                test_line = ' '.join(current_line + [word])
                test_bbox = draw.textbbox((0, 0), test_line, font=body_font)
                if test_bbox[2] - test_bbox[0] <= width - 200:  # Leave margin
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                        current_line = [word]
                    else:
                        lines.append(word)
            
            if current_line:
                lines.append(' '.join(current_line))
            
            y_pos = 350
            for line in lines:
                line_bbox = draw.textbbox((0, 0), line, font=body_font)
                line_width = line_bbox[2] - line_bbox[0]
                draw.text(
                    ((width - line_width) // 2, y_pos),
                    line,
                    fill=text_color,
                    font=body_font
                )
                y_pos += 25
        
        # Date information
        y_pos = 500
        if credential_data.get('issued_at'):
            issue_date = datetime.fromisoformat(credential_data['issued_at'].replace('Z', '+00:00'))
            date_text = f"Issued on: {issue_date.strftime('%B %d, %Y')}"
            date_bbox = draw.textbbox((0, 0), date_text, font=small_font)
            date_width = date_bbox[2] - date_bbox[0]
            draw.text(
                ((width - date_width) // 2, y_pos),
                date_text,
                fill=text_color,
                font=small_font
            )
            y_pos += 25
        
        # Credential ID
        cred_id_text = f"Credential ID: {credential_data['credential_id']}"
        cred_id_bbox = draw.textbbox((0, 0), cred_id_text, font=small_font)
        cred_id_width = cred_id_bbox[2] - cred_id_bbox[0]
        draw.text(
            ((width - cred_id_width) // 2, y_pos + 20),
            cred_id_text,
            fill=text_color,
            font=small_font
        )
        
        # QR Code
        if credential_data.get('verification_url'):
            qr_code_data = generate_qr_code(credential_data['verification_url'], size=120)
            if qr_code_data.startswith('data:image/png;base64,'):
                qr_image_data = base64.b64decode(qr_code_data.split(',')[1])
                qr_image = PILImage.open(BytesIO(qr_image_data))
                
                # Paste QR code in bottom right corner
                qr_x = width - 150
                qr_y = height - 150
                img.paste(qr_image, (qr_x, qr_y))
        
        # Save image
        img.save(output_path, 'PNG', quality=95)
        return output_path
    
    def generate_credential_files(
        self,
        credential_id: str,
        credential_data: Dict[str, Any],
        template_design: Dict[str, Any]
    ) -> Dict[str, str]:
        """Generate both PDF and PNG files for a credential."""
        
        # File paths
        pdf_path = os.path.join(self.credentials_dir, f"{credential_id}.pdf")
        png_path = os.path.join(self.credentials_dir, f"{credential_id}.png")
        
        # Generate files
        self.generate_pdf(credential_data, template_design, pdf_path)
        self.generate_png(credential_data, template_design, png_path)
        
        return {
            'pdf_path': pdf_path,
            'png_path': png_path
        }

