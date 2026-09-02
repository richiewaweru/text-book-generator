# General Lesson Spec Target

Do not invent a subject-spec framework now. Promote the existing `backend/resources/specs/lesson.yaml` as the single production general lesson spec.

It already has the desired broad arc:
```text
orient -> build -> model -> practice -> close
```
and preferred/allowed/forbidden component lists.

The spec answers:
1. What roles normally make up a lesson?
2. What must each role accomplish?
3. Which Lectio components may perform it?
4. Which are preferred/forbidden?
5. What depth/visual/budget constraints apply?

It does not choose exact content or force one component per subject.

### Candidate calculation
For a role compute deterministically:
```text
spec preferred+allowed
INTERSECT template available components
MINUS role forbidden
MINUS global forbidden
MINUS manual-only / generation-excluded
APPLY remaining component budget + max-per-section
```

Subject-specific overlays are deferred and should later be additive constraints on this general spec.
