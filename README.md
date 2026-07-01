# Vision Fallback Plugin for Agent Zero

> Route image analysis to a dedicated vision model when your main chat model doesn't support vision.

## Problem

Agent Zero sends images directly to the main chat model. If that model doesn't support vision (e.g., `glm-5.2`, `llama3`, and many text-only models), the API returns an error:

```
messages.content.type is invalid, allowed values: ['text']
```

This plugin solves that by intercepting images, sending them to a **dedicated vision model**, and inserting the **text description** into the conversation instead of raw image blocks.

## How It Works

```
User loads image
       ↓
Plugin checks: does chat_model support vision?
   ├─ YES → sends image normally (passthrough)
   └─ NO  → sends image to dedicated vision model
            → gets text description
            → inserts description into conversation
```

## Installation

### Option A: Symlink (Development)
```bash
ln -s /path/to/vision-fallback /a0/usr/plugins/vision_fallback
```

### Option B: Copy
```bash
cp -r /path/to/vision-fallback /a0/usr/plugins/vision_fallback
```

Then restart Agent Zero.

## Configuration

Go to **Settings → Agent → Vision Fallback** in the Agent Zero web UI.

| Setting | Description | Default |
|---------|-------------|---------|
| **Enabled** | Toggle the fallback on/off | `true` |
| **Provider** | LiteLLM provider (openrouter, ollama, openai, etc.) | `openrouter` |
| **Model Name** | Vision model to use | `google/gemini-2.5-flash` |
| **API Key** | Key for the provider (leave empty for local) | `""` |
| **API Base** | Custom endpoint URL | `""` |
| **Prompt** | Prompt sent to the vision model | *(see config)* |

## Recommended Vision Models

| Model | Provider | Cost | Quality |
|-------|----------|------|---------|
| `google/gemini-2.5-flash` | OpenRouter | ~0$ | Excellent |
| `llama3.2-vision` | Ollama (local) | Free | Good |
| `gpt-4o-mini` | OpenAI/OpenRouter | Very cheap | Excellent |
| `anthropic/claude-haiku-4.5` | OpenRouter | Cheap | Excellent |

## Requirements

- Agent Zero framework
- A vision-capable model (via any LiteLLM-supported provider)

## License

MIT
