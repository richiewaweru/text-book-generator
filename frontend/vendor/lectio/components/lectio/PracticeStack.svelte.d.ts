import type { PracticeContent } from '../../types';
type PracticeStackMode = 'accordion' | 'flat-list';
type $$ComponentProps = {
    content: PracticeContent;
    mode?: PracticeStackMode;
};
declare const PracticeStack: import("svelte").Component<$$ComponentProps, {}, "">;
type PracticeStack = ReturnType<typeof PracticeStack>;
export default PracticeStack;
