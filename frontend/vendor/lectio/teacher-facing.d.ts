/**
 * Teacher-facing labels for the lesson builder palette.
 * Every component id in the registry must have an entry.
 */
export declare const TEACHER_LOOKUP: Record<string, {
    teacherLabel: string;
    teacherDescription: string;
}>;
export declare function teacherFor(componentId: string): {
    teacherLabel: string;
    teacherDescription: string;
};
