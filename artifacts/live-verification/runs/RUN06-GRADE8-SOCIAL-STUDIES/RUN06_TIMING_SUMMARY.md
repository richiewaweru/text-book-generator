# Run 6 timing summary (sanitized)

Times are derived from persisted UTC timestamps. The run has one observation;
therefore the reported single-run medians equal the observed values and no
cross-SHA statistics are mixed.

| Interval | Single-run median | Observed range |
|---|---:|---:|
| generation creation → first `block_ready` | 778.353 s | 778.353–778.353 s |
| generation creation → terminal completion | 917.904 s | 917.904–917.904 s |
| generation creation → Builder row creation | 917.972 s | 917.972–917.972 s |
| Builder creation → persisted save/reload update | 1,144.848 s | 1,144.848–1,144.848 s |

Six provider calls were persisted for the generation. Their individual latency
values are intentionally not published; transport/model/attempt details are
summarized in the network and database evidence. No transport retry or repair
attempt occurred.
