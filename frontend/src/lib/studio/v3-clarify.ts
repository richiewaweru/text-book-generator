import type { V3InputForm } from '$lib/types/v3';

export function hasRequiredStructuredFields(form: V3InputForm): boolean {
	if (!form.grade_level.trim()) return false;
	if (!form.subject.trim()) return false;
	if (!form.topic.trim() || form.topic.trim().length < 3) return false;
	if (!(form.duration_minutes >= 15 && form.duration_minutes <= 90)) return false;
	if (!form.lesson_mode.trim()) return false;
	if (!form.learner_level.trim()) return false;
	if (!form.reading_level.trim()) return false;
	if (!form.language_support.trim()) return false;
	if (!form.prior_knowledge_level.trim()) return false;
	if (!form.intended_outcome.trim()) return false;
	return true;
}

