# LLM Router - OpenAI API compatible router for multiple LLM backends
# Copyright (C) 2025
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Pydantic models for OpenAI API compatibility.
"""
from typing import List, Optional, Dict, Any, Union, Literal
from pydantic import BaseModel, Field


class Message(BaseModel):
    """A message in a chat completion."""
    role: Literal["system", "user", "assistant", "function"] = Field(
        ..., description="The role of the message author"
    )
    content: Optional[str] = Field(
        None, description="The content of the message"
    )
    name: Optional[str] = Field(
        None, description="The name of the message author"
    )


class ChatCompletionRequest(BaseModel):
    """Request model for chat completions."""
    model: str = Field(..., description="ID of the model to use")
    messages: List[Message] = Field(
        ..., description="A list of messages comprising the conversation so far"
    )
    temperature: Optional[float] = Field(
        1.0, ge=0.0, le=2.0, description="Sampling temperature to use"
    )
    top_p: Optional[float] = Field(
        1.0, ge=0.0, le=1.0, description="Nucleus sampling parameter"
    )
    n: Optional[int] = Field(
        1, ge=1, description="Number of chat completion choices to generate"
    )
    stream: Optional[bool] = Field(
        False, description="Whether to stream back partial progress"
    )
    stop: Optional[Union[str, List[str]]] = Field(
        None, description="Up to 4 sequences where the API will stop generating"
    )
    max_tokens: Optional[int] = Field(
        None, ge=1, description="Maximum number of tokens to generate"
    )
    presence_penalty: Optional[float] = Field(
        0.0, ge=-2.0, le=2.0, description="Presence penalty parameter"
    )
    frequency_penalty: Optional[float] = Field(
        0.0, ge=-2.0, le=2.0, description="Frequency penalty parameter"
    )
    logit_bias: Optional[Dict[str, float]] = Field(
        None, description="Modify the likelihood of specified tokens"
    )
    user: Optional[str] = Field(
        None, description="A unique identifier representing your end-user"
    )


class Choice(BaseModel):
    """A completion choice."""
    index: int = Field(..., description="The index of this choice")
    message: Message = Field(..., description="The message for this choice")
    finish_reason: Optional[Literal["stop", "length", "content_filter"]] = Field(
        None, description="The reason the model stopped generating tokens"
    )


class Usage(BaseModel):
    """Usage statistics for the completion request."""
    prompt_tokens: int = Field(..., description="Number of tokens in the prompt")
    completion_tokens: int = Field(..., description="Number of tokens in the completion")
    total_tokens: int = Field(..., description="Total number of tokens used")


class ChatCompletionResponse(BaseModel):
    """Response model for chat completions."""
    id: str = Field(..., description="A unique identifier for the chat completion")
    object: Literal["chat.completion"] = Field(
        "chat.completion", description="The object type"
    )
    created: int = Field(..., description="The Unix timestamp of when the completion was created")
    model: str = Field(..., description="The model used for the chat completion")
    choices: List[Choice] = Field(..., description="A list of chat completion choices")
    usage: Usage = Field(..., description="Usage statistics for the completion request")
    
    # Router metadata (optional, not part of OpenAI standard)
    router: Optional[Dict[str, Any]] = Field(None, description="Router processing information")
    
    model_config = {"extra": "ignore"}


class ErrorResponse(BaseModel):
    """Error response model."""
    error: Dict[str, Any] = Field(..., description="Error details")


class ModelInfo(BaseModel):
    """Model information."""
    id: str = Field(..., description="The model identifier")
    object: Literal["model"] = Field("model", description="The object type")
    created: int = Field(..., description="The Unix timestamp of when the model was created")
    owned_by: str = Field(..., description="The organization that owns the model")


class ModelListResponse(BaseModel):
    """Response model for listing models."""
    object: Literal["list"] = Field("list", description="The object type")
    data: List[ModelInfo] = Field(..., description="The list of models")
