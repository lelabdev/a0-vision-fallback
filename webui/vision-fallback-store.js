import { createStore } from "/js/AlpineStore.js";
import { fetchApi } from "/js/api.js";

export const store = createStore("visionFallbackStore", {
  available: [],
  unavailable: [],
  loaded: false,

  async loadProviders() {
    if (this.loaded) return;
    try {
      const res = await fetchApi("/api/plugins/a0_vision_fallback/available_providers");
      const data = await res.json();
      this.available = data.available || [];
      this.unavailable = data.unavailable || [];
    } catch (e) {
      // Fallback: show all as available with manual key entry
      this.available = [{ id: "openrouter", label: "OpenRouter", has_key: false, env_var: "API_KEY_OPENROUTER" }];
      this.unavailable = [];
    }
    this.loaded = true;
  },

  isConfigured(providerId) {
    const p = this.available.find((p) => p.id === providerId);
    return p && p.has_key;
  },

  getEnvVar(providerId) {
    const p = [...this.available, ...this.unavailable].find((p) => p.id === providerId);
    return p ? p.env_var : "";
  },
});
