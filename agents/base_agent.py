"""
Agent Base Class
Provides common functionality for all specialized agents
"""
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

class BaseAgent(ABC):
    """Base class for all test generation agents"""
    
    def __init__(self, config: Dict[str, Any], llm_client: Any):
        self.config = config
        self.llm_client = llm_client
        self.logger = logging.getLogger(self.__class__.__name__)
        self.start_time = None
        self.end_time = None
        
    @abstractmethod
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent's main task"""
        pass
    
    def log_start(self):
        """Log agent start"""
        self.start_time = datetime.now()
        self.logger.info(f"{'='*60}")
        self.logger.info(f"Starting {self.__class__.__name__}")
        self.logger.info(f"{'='*60}")
    
    def log_end(self):
        """Log agent completion"""
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()
        self.logger.info(f"Completed {self.__class__.__name__} in {duration:.2f} seconds")
        self.logger.info(f"{'='*60}\n")
    
    def call_llm(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.7) -> str:
        """Call the LLM with given prompts"""
        try:
            # This will be implemented based on the LLM provider
            response = self.llm_client.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature
            )
            return response
        except Exception as e:
            self.logger.error(f"LLM call failed: {str(e)}")
            raise
    
    def validate_output(self, output: Dict[str, Any]) -> bool:
        """Validate agent output"""
        if not output:
            self.logger.error("Output is empty")
            return False
        return True
    
    def save_output(self, output: Dict[str, Any], filepath: str):
        """Save agent output to file"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(output, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Output saved to {filepath}")
        except Exception as e:
            self.logger.error(f"Failed to save output: {str(e)}")
            raise
