import type { SectionRole, VisualPolicy } from '$lib/types';

const ROLE_LABELS: Record<SectionRole, string> = {
	intro: 'Intro',
	explain: 'Explain',
	practice: 'Practice',
	summary: 'Summary',
	process: 'Process',
	compare: 'Compare',
	timeline: 'Timeline',
	visual: 'Visual',
	discover: 'Discover'
};

const ROLE_TONES: Record<SectionRole, 'intro' | 'explain' | 'practice' | 'summary' | 'neutral'> = {
	intro: 'intro',
	explain: 'explain',
	practice: 'practice',
	summary: 'summary',
	process: 'explain',
	compare: 'practice',
	timeline: 'summary',
	visual: 'intro',
	discover: 'neutral'
};

const HEAVY_COMPONENTS = new Set([
	'diagram-block',
	'diagram-series',
	'diagram-compare',
	'simulation-block',
	'simulation'
]);

const COMPONENT_LABELS: Record<string, string> = {
	'hook-hero': 'Hook hero',
	'explanation-block': 'Explanation',
	'practice-stack': 'Practice stack',
	'what-next-bridge': 'What next bridge',
	'worked-example-card': 'Worked example',
	'diagram-block': 'Diagram',
	'diagram-series': 'Diagram series',
	'diagram-compare': 'Compare diagram',
	'simulation-block': 'Simulation',
	'section-header': 'Section header',
	'process-steps': 'Process steps',
	'student-textbox': 'Student textbox',
	'summary-block': 'Summary'
};

export function roleLabel(role: SectionRole): string {
	return ROLE_LABELS[role] ?? role;
}

export function roleTone(role: SectionRole): 'intro' | 'explain' | 'practice' | 'summary' | 'neutral' {
	return ROLE_TONES[role] ?? 'neutral';
}

export function isHeavyComponent(componentId: string): boolean {
	return HEAVY_COMPONENTS.has(componentId);
}

export function componentLabel(componentId: string): string {
	return COMPONENT_LABELS[componentId] ?? componentId.replace(/-/g, ' ');
}

export function visualPolicyLabel(policy: VisualPolicy | null): string | null {
	if (!policy?.required) {
		return null;
	}

	if (policy.mode === 'svg') {
		return 'SVG diagram';
	}

	if (policy.mode === 'image') {
		return 'Image diagram';
	}

	return 'Visual required';
}
