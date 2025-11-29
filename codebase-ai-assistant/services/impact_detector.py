"""Impact detection service for analyzing code change impacts."""
from typing import Dict, List, Any
from services.claude_service import ClaudeService
from services.repository_analyzer import RepositoryAnalyzer


# Risk level criteria
RISK_CRITERIA = {
    'low': {
        'max_affected_files': 2,
        'has_overlaps': False,
        'affects_core': False,
        'auto_proceed': True
    },
    'medium': {
        'max_affected_files': 5,
        'has_overlaps': True,
        'affects_core': False,
        'auto_proceed': False,
        'requires_review': True
    },
    'high': {
        'max_affected_files': 10,
        'has_overlaps': True,
        'affects_core': True,
        'auto_proceed': False,
        'requires_approval': True
    },
    'critical': {
        'affects_core': True,
        'breaking_changes': True,
        'auto_proceed': False,
        'requires_approval': True,
        'manual_review_required': True
    }
}


class ImpactDetector:
    """Detect impacts of code changes."""
    
    def __init__(self, claude_service: ClaudeService, repository_analyzer: RepositoryAnalyzer):
        """Initialize impact detector."""
        self.claude = claude_service
        self.analyzer = repository_analyzer
    
    def analyze_change_impact(self, change_request: str, repo_id: int, 
                             repo_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze what a change request would affect.
        
        Steps:
        1. Parse the change request to identify target areas
        2. Find affected files using dependency graph
        3. Identify overlapping features
        4. Use Claude to assess complexity and risks
        5. Calculate risk level
        6. Generate warnings
        
        Returns:
            Dictionary with risk_level, affected_files, affected_features, warnings, recommendation, should_proceed
        """
        # Get repository structure
        structure = repo_data.get('structure_json', {}).get('structure', {})
        dependency_graph = repo_data.get('structure_json', {}).get('dependency_graph', {})
        pdf_documents = repo_data.get('pdf_documents', {})
        
        # Use Claude to analyze impact
        repo_context = {
            'structure': structure,
            'dependency_graph': dependency_graph,
            'pdf_documents': pdf_documents.get('text', '')  # Include PDF context
        }
        
        claude_analysis = self.claude.analyze_impact(change_request, repo_context)
        
        # Find affected modules using dependency graph
        affected_files = claude_analysis.get('affected_files', [])
        if not affected_files:
            # Fallback: try to find files based on keywords
            affected_files = self._find_files_by_keywords(change_request, structure)
        
        # Expand affected files using dependency graph
        all_affected_files = self._expand_affected_files(affected_files, dependency_graph)
        
        # Detect feature overlaps
        existing_features = self._extract_features(structure)
        overlaps = self.detect_feature_overlap(change_request, existing_features)
        
        # Calculate risk level
        risk_level = self.calculate_risk_level({
            'affected_files': all_affected_files,
            'has_overlaps': len(overlaps) > 0,
            'affects_core': self._affects_core_modules(all_affected_files),
            'warnings': claude_analysis.get('warnings', [])
        })
        
        # Determine if should proceed
        criteria = RISK_CRITERIA.get(risk_level, RISK_CRITERIA['medium'])
        should_proceed = criteria.get('auto_proceed', False)
        requires_approval = criteria.get('requires_approval', False)
        
        return {
            'risk_level': risk_level,
            'affected_files': all_affected_files,
            'affected_features': claude_analysis.get('affected_features', []),
            'warnings': claude_analysis.get('warnings', []) + [o.get('conflict_description', '') for o in overlaps],
            'recommendation': claude_analysis.get('recommendation', ''),
            'should_proceed': should_proceed,
            'requires_approval': requires_approval,
            'overlaps': overlaps
        }
    
    def find_affected_modules(self, target_file: str, dependency_graph: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Find all modules that depend on target file.
        
        Uses:
        - Import relationships
        - Function call relationships
        - Inheritance relationships
        
        Returns:
            List of affected modules with relationship types
        """
        affected = []
        edges = dependency_graph.get('edges', [])
        
        # Find all edges that reference the target file
        for edge in edges:
            source = edge.get('source', '')
            target = edge.get('target', '')
            edge_type = edge.get('type', '')
            
            if target_file in target or target_file in source:
                affected.append({
                    'file_path': target if target_file in source else source,
                    'relationship_type': edge_type,
                    'dependency_strength': 1.0  # Simplified for now
                })
        
        return affected
    
    def detect_feature_overlap(self, change_request: str, existing_features: List[str]) -> List[Dict[str, Any]]:
        """
        Detect if change overlaps with existing features.
        
        Returns:
            List of overlaps with descriptions
        """
        overlaps = []
        change_lower = change_request.lower()
        
        # Simple keyword-based overlap detection
        for feature in existing_features:
            feature_lower = feature.lower()
            # Check if change request mentions similar concepts
            if any(word in change_lower for word in feature_lower.split() if len(word) > 4):
                overlaps.append({
                    'feature_name': feature,
                    'overlap_type': 'potential_conflict',
                    'conflict_description': f"Change may conflict with existing feature: {feature}"
                })
        
        return overlaps
    
    def calculate_risk_level(self, impact_data: Dict[str, Any]) -> str:
        """
        Calculate risk level based on multiple factors.
        
        Factors:
        - Number of affected files
        - Presence of overlapping features
        - Complexity of changes
        - Core vs peripheral modules
        
        Returns:
            'low' | 'medium' | 'high' | 'critical'
        """
        affected_files_count = len(impact_data.get('affected_files', []))
        has_overlaps = impact_data.get('has_overlaps', False)
        affects_core = impact_data.get('affects_core', False)
        warnings_count = len(impact_data.get('warnings', []))
        
        # Critical: affects core and has many warnings
        if affects_core and warnings_count > 3:
            return 'critical'
        
        # High: affects core or many files
        if affects_core or affected_files_count > 8:
            return 'high'
        
        # Medium: some overlaps or moderate file count
        if has_overlaps or affected_files_count > 3:
            return 'medium'
        
        # Low: minimal impact
        return 'low'
    
    def _expand_affected_files(self, initial_files: List[str], 
                              dependency_graph: Dict[str, Any]) -> List[str]:
        """Expand affected files using dependency graph."""
        all_files = set(initial_files)
        edges = dependency_graph.get('edges', [])
        
        # Find files that import or depend on initial files
        for edge in edges:
            source = edge.get('source', '')
            target = edge.get('target', '')
            edge_type = edge.get('type', '')
            
            # If source is affected and imports target, add target
            if any(af in source for af in initial_files) and edge_type == 'imports':
                all_files.add(target)
        
        return list(all_files)
    
    def _find_files_by_keywords(self, change_request: str, structure: Dict[str, Any]) -> List[str]:
        """Find files based on keywords in change request."""
        keywords = change_request.lower().split()
        relevant_files = []
        
        for file_info in structure.get('files', []):
            file_path = file_info['file_path'].lower()
            for keyword in keywords:
                if len(keyword) > 3 and keyword in file_path:
                    relevant_files.append(file_info['file_path'])
                    break
        
        return relevant_files
    
    def _extract_features(self, structure: Dict[str, Any]) -> List[str]:
        """Extract feature names from structure."""
        features = []
        
        # Extract from class names
        for cls in structure.get('classes', []):
            cls_name = cls.get('name', '')
            if cls_name and not cls_name.startswith('_'):
                features.append(cls_name)
        
        # Extract from function names (top-level)
        for func in structure.get('functions', []):
            func_name = func.get('name', '')
            if func_name and not func_name.startswith('_'):
                features.append(func_name)
        
        return features
    
    def _affects_core_modules(self, files: List[str]) -> bool:
        """Check if changes affect core modules."""
        core_keywords = ['app.py', 'config', 'auth', 'database', 'model', 'service']
        return any(any(keyword in f.lower() for keyword in core_keywords) for f in files)

