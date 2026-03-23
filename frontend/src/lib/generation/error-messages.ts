export function friendlyGenerationErrorMessage(
	error: string | null,
	type: string | null,
	_code: string | null = null
): string {
	if (type === 'provider_error') {
		return error ?? 'The AI provider rejected the request. Check your provider configuration and try again.';
	}
	if (type === 'pipeline_error') {
		return 'The generation pipeline encountered an error. Please try again with different input.';
	}
	return error ?? 'Generation failed unexpectedly.';
}
