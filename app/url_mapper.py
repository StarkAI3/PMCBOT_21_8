import json
import os
from typing import Dict, List, Optional

class URLMapper:
    def __init__(self, mapping_file_path: str = "comprehensive_all_api_mappings.json"):
        self.mapping_file_path = mapping_file_path
        self.api_to_frontend_map = {}
        self.load_mappings()
    
    def load_mappings(self):
        """Load API to frontend URL mappings from the JSON file."""
        try:
            if os.path.exists(self.mapping_file_path):
                with open(self.mapping_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    mappings = data.get('mappings', [])
                    
                    for mapping in mappings:
                        api_url = mapping.get('api_url', '')
                        frontend_url = mapping.get('frontend_url', '')
                        status = mapping.get('status', '')
                        
                        # Only include mappings that have a valid frontend URL and status is "Found"
                        if frontend_url and status == "Found":
                            self.api_to_frontend_map[api_url] = frontend_url
                            
                print(f"Loaded {len(self.api_to_frontend_map)} URL mappings")
            else:
                print(f"Warning: Mapping file {self.mapping_file_path} not found")
        except Exception as e:
            print(f"Error loading URL mappings: {e}")
    
    def get_frontend_url(self, api_url: str) -> Optional[str]:
        """Convert a backend API URL to its corresponding frontend URL."""
        return self.api_to_frontend_map.get(api_url)
    
    def convert_urls_in_text(self, text: str) -> str:
        """Convert all backend URLs in a text to their frontend equivalents."""
        if not text:
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
        """Get all available frontend URLs."""
        return list(self.api_to_frontend_map.values())
    
    def search_mappings_by_keyword(self, keyword: str) -> List[Dict]:
        """Search for mappings that contain the keyword in either API URL or frontend URL."""
        results = []
        keyword_lower = keyword.lower()
        
        for api_url, frontend_url in self.api_to_frontend_map.items():
            if (keyword_lower in api_url.lower() or 
                keyword_lower in frontend_url.lower()):
                results.append({
                    'api_url': api_url,
                    'frontend_url': frontend_url
                })
        
        return results

# Global instance
url_mapper = URLMapper() 