import json
import re
from typing import List, Dict, Optional, AsyncGenerator
from dataclasses import dataclass
from enum import Enum

class AgentAction(Enum):
    THINK = "think"
    CODE = "code"
    EXPLAIN = "explain"
    QUIZ = "quiz"
    SUGGEST = "suggest"
    EXECUTE = "execute"
    COMPLETE = "complete"

@dataclass
class AgentStep:
    action: AgentAction
    content: str
    metadata: Optional[Dict] = None

class AgentEngine:
    """
    Agentic engine that processes user queries through structured thinking steps.
    """
    
    def __init__(self):
        self.action_patterns = {
            AgentAction.THINK: r"<think>(.*?)</think>",
            AgentAction.CODE: r"<code(?:\s+lang=\"(\w+)\")?>(.+?)</code>",
            AgentAction.EXPLAIN: r"<explain>(.*?)</explain>",
            AgentAction.QUIZ: r"<quiz>(.*?)</quiz>",
            AgentAction.SUGGEST: r"<suggest>(.*?)</suggest>",
            AgentAction.EXECUTE: r"<execute>(.*?)</execute>",
        }
        
    def create_agent_prompt(self, user_question: str, user_profile: Dict, roadmap: Optional[Dict] = None) -> str:
        """
        Creates a prompt that instructs the LLM to think and act like an agent.
        """
        system_prompt = f"""You are an AI coding mentor helping a {user_profile.get('experience', 'beginner')} learner.

Learning Profile:
- Style: {user_profile.get('learning_style', 'balanced')}
- Goal: {user_profile.get('goal', 'general programming')}

INSTRUCTIONS: You MUST structure your response using these exact XML tags:

1. First, think about the question:
<think>Write your analysis of what the user needs</think>

2. Then explain the concept:
<explain>Write a clear explanation</explain>

3. Show code example:
<code lang="python">Write example code here</code>

4. Optionally test their understanding:
<quiz>Ask a question about the concept</quiz>

5. Suggest next steps:
<suggest>What they should learn or try next</suggest>

RESPOND TO THIS QUESTION: {user_question}

Remember: You MUST use the XML tags above to structure your response."""
        
        return system_prompt
    
    def parse_agent_response(self, response: str) -> List[AgentStep]:
        """
        Parses the LLM response to extract structured agent steps.
        """
        steps = []
        
        # Extract thinking steps
        for action, pattern in self.action_patterns.items():
            matches = re.finditer(pattern, response, re.DOTALL)
            for match in matches:
                if action == AgentAction.CODE:
                    language = match.group(1) or "python"
                    content = match.group(2).strip()
                    steps.append(AgentStep(
                        action=action,
                        content=content,
                        metadata={"language": language}
                    ))
                else:
                    content = match.group(1).strip()
                    steps.append(AgentStep(action=action, content=content))
        
        # If no structured content found, treat entire response as explanation
        if not steps and response.strip():
            steps.append(AgentStep(action=AgentAction.EXPLAIN, content=response.strip()))
        
        return steps
    
    async def process_streaming_response(self, stream_generator: AsyncGenerator) -> AsyncGenerator[Dict, None]:
        """
        Processes streaming tokens and yields structured agent actions.
        """
        buffer = ""
        current_tag = None
        current_content = ""
        
        async for chunk in stream_generator:
            if isinstance(chunk, dict) and "token" in chunk:
                buffer += chunk["token"]
                
                # Check for opening tags
                for action in AgentAction:
                    tag_name = action.value
                    open_tag = f"<{tag_name}"
                    close_tag = f"</{tag_name}>"
                    
                    if not current_tag and open_tag in buffer:
                        # Found opening tag
                        pre_tag = buffer.split(open_tag)[0]
                        if pre_tag.strip():
                            yield {
                                "type": "agent_action",
                                "action": "explain",
                                "content": pre_tag.strip()
                            }
                        current_tag = tag_name
                        buffer = buffer.split(open_tag, 1)[1]
                        
                        # Handle code language attribute
                        if tag_name == "code" and 'lang="' in buffer:
                            lang_match = re.match(r'lang="(\w+)">', buffer)
                            if lang_match:
                                yield {
                                    "type": "agent_action",
                                    "action": "code_start",
                                    "language": lang_match.group(1)
                                }
                                buffer = buffer[lang_match.end():]
                        elif ">" in buffer:
                            buffer = buffer.split(">", 1)[1]
                    
                    elif current_tag == tag_name and close_tag in buffer:
                        # Found closing tag
                        content, remaining = buffer.split(close_tag, 1)
                        current_content += content
                        
                        yield {
                            "type": "agent_action",
                            "action": current_tag,
                            "content": current_content.strip()
                        }
                        
                        current_tag = None
                        current_content = ""
                        buffer = remaining
                
                # Stream content within tags
                if current_tag and len(buffer) > 100:
                    # Stream partial content to avoid buffering too much
                    yield {
                        "type": "partial",
                        "action": current_tag,
                        "content": buffer[:80]
                    }
                    current_content += buffer[:80]
                    buffer = buffer[80:]
            
            elif isinstance(chunk, dict) and chunk.get("done"):
                # Handle any remaining content
                if buffer.strip():
                    if current_tag:
                        yield {
                            "type": "agent_action",
                            "action": current_tag,
                            "content": (current_content + buffer).strip()
                        }
                    else:
                        yield {
                            "type": "agent_action",
                            "action": "explain",
                            "content": buffer.strip()
                        }
                
                yield {"type": "done"}
                break

    def format_step_for_display(self, step: AgentStep) -> str:
        """
        Formats an agent step for user display.
        """
        if step.action == AgentAction.THINK:
            return f"🤔 Thinking: {step.content}\n"
        elif step.action == AgentAction.CODE:
            lang = step.metadata.get("language", "python") if step.metadata else "python"
            return f"```{lang}\n{step.content}\n```\n"
        elif step.action == AgentAction.EXPLAIN:
            return f"📚 {step.content}\n"
        elif step.action == AgentAction.QUIZ:
            return f"❓ Quiz: {step.content}\n"
        elif step.action == AgentAction.SUGGEST:
            return f"💡 Suggestion: {step.content}\n"
        elif step.action == AgentAction.EXECUTE:
            return f"▶️ Executing:\n```python\n{step.content}\n```\n"
        else:
            return step.content + "\n"