import json
import os
from typing import Dict, List, Optional

class URLMapper:
    def __init__(self, mapping_file_path: str = "clean_api_frontend_mappings.json"):
        self.mapping_file_path = mapping_file_path
        self.mappings_data = None
        self.load_mappings()
    
    def load_mappings(self):
        """Load the complete mappings data from JSON file for direct lookup."""
        try:
            if os.path.exists(self.mapping_file_path):
                with open(self.mapping_file_path, 'r', encoding='utf-8') as f:
                    self.mappings_data = json.load(f)
                print(f"Loaded clean mappings data from {self.mapping_file_path}")
                print(f"Total mappings: {self.mappings_data.get('total_mappings', 0)}")
                print(f"Correct mappings: {self.mappings_data.get('correct_mappings', 0)}")
            else:
                print(f"Warning: Mapping file {self.mapping_file_path} not found")
        except Exception as e:
            print(f"Error loading URL mappings: {e}")
    
    def get_frontend_url(self, api_url: str) -> Optional[str]:
        """Direct lookup of frontend URL from manually verified mappings."""
        if not self.mappings_data:
            return None
            
        mappings = self.mappings_data.get('mappings', [])
        
        # Direct search through mappings for exact API URL match
        for mapping in mappings:
            if (mapping.get('api_url') == api_url and 
                mapping.get('manual_verdict') == 'correct' and
                mapping.get('frontend_url')):
                return mapping.get('frontend_url')
        
        return None
    
    def convert_urls_in_text(self, text: str) -> str:
        """Convert all backend URLs in a text to their frontend equivalents using direct lookup."""
        if not text or not self.mappings_data:
            return text
            
        # Find all URLs in the text
        import re
        url_pattern = r'https?://[^\s\)]+'
        urls = re.findall(url_pattern, text)
        
        converted_text = text
        for url in urls:
            frontend_url = self.get_frontend_url(url)
            if frontend_url:
                converted_text = converted_text.replace(url, frontend_url)
        
        return converted_text
    
    def get_all_frontend_urls(self) -> List[str]:
        """Get all manually verified frontend URLs."""
        if not self.mappings_data:
            return []
            
        frontend_urls = []
        mappings = self.mappings_data.get('mappings', [])
        
        for mapping in mappings:
            if (mapping.get('manual_verdict') == 'correct' and 
                mapping.get('frontend_url')):
                frontend_urls.append(mapping.get('frontend_url'))
        
        return frontend_urls
    
    def search_mappings_by_keyword(self, keyword: str) -> List[Dict]:
        """Search for mappings that contain the keyword using direct JSON lookup."""
        if not self.mappings_data:
            return []
            
        results = []
        keyword_lower = keyword.lower()
        mappings = self.mappings_data.get('mappings', [])
        
        for mapping in mappings:
            if (mapping.get('manual_verdict') == 'correct' and
                mapping.get('frontend_url') and
                (keyword_lower in mapping.get('api_url', '').lower() or 
                 keyword_lower in mapping.get('frontend_url', '').lower())):
                results.append({
                    'api_url': mapping.get('api_url'),
                    'frontend_url': mapping.get('frontend_url')
                })
        
        return results

# Global instance
url_mapper = URLMapper() 