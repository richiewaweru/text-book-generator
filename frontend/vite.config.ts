import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

// Vite exposes environment variables via import.meta.env in both dev and build
const apiTarget = (import.meta as any).env?.VITE_API_TARGET ?? 'http://localhost:8000';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		proxy: {
			'/api': apiTarget,
			'/health': apiTarget
		}
	}
});
