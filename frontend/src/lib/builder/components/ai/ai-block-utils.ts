import { getEmptyContent } from 'lectio';

/** True when block content is not the default empty shape (shows Improve in AI UI). */
export function blockHasDistinctContent(
	componentId: string,
	content: Record<string, unknown>
): boolean {
	return JSON.stringify(content) !== JSON.stringify(getEmptyContent(componentId));
}
