# Vision Fallback Plugin for Agent Zero

> Route image analysis to a dedicated vision model when your main chat model doesn't support vision.

[![GitHub](https://img.shields.io/badge/GitHub-lelabdev%2Fa0--vision--fallback-blue)](https://github.com/lelabdev/a0-vision-fallback)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## The Problem

Many affordable or lightweight LLMs (like `glm-5.2`, `llama3`, `deepseek`, etc.) are **text-only**. When Agent Zero tries to send an image to these models, the API crashes with:

```
messages.content.type is invalid, allowed values: ['text']
```

Agent Zero has no native way to use a **separate vision model** — images always go to the main chat model.

## The Solution

This plugin uses an **extension hook** (`message_loop_prompts_after`) to intercept messages just before they reach the LLM. When images are detected:

1. Each image is sent to a **dedicated vision model** (configurable)
2. The vision model returns a **text description**
3. The `image_url` block is replaced with the text description
4. The main chat model receives **only text** — no more crashes

```
User loads image
     ↓
Extension hook intercepts message
     ↓
Image → Vision Model (e.g. Gemini Flash) → "A red circle, blue rectangle..."
     ↓
Text replaces image in conversation
     ↓
Main chat model (text-only) → ✅ Works!
```

## Features

- 🔌 **Works with any text-only model** — no need to change your main LLM
- 🔑 **Auto-resolves API keys** from Agent Zero `.env` (no duplicate configuration)
- 🎯 **Smart provider detection** — shows ✅ badge for providers with keys configured
- 💾 **Hash-based cache** — avoids re-describing the same image twice
- 🌗 **Dark mode compatible** — uses Agent Zero CSS variables
- 🔗 **LiteLLM-powered** — supports OpenRouter, Ollama Cloud, OpenAI, Anthropic, Google, Groq, and more

## Installation

### Via Symlink (Development)
```bash
ln -s /path/to/a0-vision-fallback /a0/usr/plugins/a0_vision_fallback
```

### Via Copy
```bash
cp -r /path/to/a0-vision-fallback /a0/usr/plugins/a0_vision_fallback
```

Restart Agent Zero after installation.

## Configuration

Go to **Settings → Agent → Vision Fallback** in the Agent Zero web UI.

| Setting | Description | Default |
|---------|-------------|---------|
| **Enable** | Toggle the plugin on/off | `true` |
| **Provider** | Vision model provider | `Ollama Cloud` |
| **Model Name** | Vision model to use | `gemini-3-flash-preview` |
| **API Key** | Custom key (optional — auto-resolved from `.env` if empty) | `""` |

### Recommended Vision Models

| Model | Provider | Vision | Cost |
|-------|----------|--------|------|
| `gemini-3-flash-preview` | Ollama Cloud | ✅ | Free |
| `llama3.2-vision` | Ollama (local) | ✅ | Free |
| `gpt-4o-mini` | OpenRouter/OpenAI | ✅ | Cheap |
| `google/gemini-2.5-flash` | OpenRouter | ✅ | ~Free |

## How It Works (Technical)

The plugin uses an Agent Zero **extension hook** (not a tool override):

- **Hook**: `extensions/python/message_loop_prompts_after/replace_images_with_descriptions.py`
- **Trigger**: Fires after prompt preparation, before LLM call
- **Logic**: Scans `loop_data.history_output` for `image_url` blocks → calls vision model → replaces with text

### File Structure

```
a0-vision-fallback/
├── plugin.yaml                    # Plugin manifest
├── default_config.yaml            # Default settings
├── extensions/
│   └── python/
│       └── message_loop_prompts_after/
│           └── replace_images_with_descriptions.py  # Main hook
├── helpers/
│   └── vision_describe.py         # Vision model API calls + cache
├── api/
│   └── available_providers.py     # API endpoint for key detection
├── webui/
│   └── config.html                # Settings UI
├── LICENSE
└── README.md
```

## Requirements

- Agent Zero framework
- A vision-capable model via any LiteLLM-supported provider

## License

MIT
