from dataclasses import dataclass


@dataclass(frozen=True)
class SessionMeshPlan:
    mesh_count: int = 100
    sessions_per_mesh: int = 400_000_000

    def validate(self):
        if self.mesh_count < 1:
            raise ValueError("mesh_count must be positive")
        if self.sessions_per_mesh < 1:
            raise ValueError("sessions_per_mesh must be positive")

    @property
    def total_sessions(self):
        self.validate()
        return self.mesh_count * self.sessions_per_mesh

    def mesh_for_session(self, session_id):
        if not 0 <= session_id < self.total_sessions:
            raise ValueError("session_id is outside the plan")
        return session_id % self.mesh_count

    def progress(self, completed_sessions):
        if not 0 <= completed_sessions <= self.total_sessions:
            raise ValueError("completed_sessions is outside the plan")
        whole, remainder = divmod(completed_sessions, self.mesh_count)
        return [whole + int(mesh_id < remainder) for mesh_id in range(self.mesh_count)]

    def steps_for_budget(self, sessions, batch_size, gradient_accumulation, world_size):
        if not 0 <= sessions <= self.total_sessions:
            raise ValueError("sessions must be within the plan")
        if min(batch_size, gradient_accumulation, world_size) < 1:
            raise ValueError("batch_size, gradient_accumulation and world_size must be positive")
        sessions_per_step = batch_size * gradient_accumulation * world_size
        if sessions % sessions_per_step:
            raise ValueError("session budget must be divisible by the global sessions per optimizer step")
        return sessions // sessions_per_step

    def session_ids(self, step_index, micro_step, rank, batch_size, gradient_accumulation, world_size):
        if step_index < 0 or not 0 <= micro_step < gradient_accumulation:
            raise ValueError("step or micro_step is out of range")
        if not 0 <= rank < world_size:
            raise ValueError("rank is outside the distributed world")
        first = (
            step_index * gradient_accumulation * world_size * batch_size
            + (micro_step * world_size + rank) * batch_size
        )
        return tuple(range(first, first + batch_size))

    def as_dict(self, completed_sessions=0):
        self.progress(completed_sessions)
        return {
            "mesh_count": self.mesh_count,
            "sessions_per_mesh": self.sessions_per_mesh,
            "target_sessions": self.total_sessions,
            "completed_sessions": completed_sessions,
            "mesh_progress": self.progress(completed_sessions),
            "session_definition": "one causal-language-model training sequence window",
            "execution_model": "logical work queues; physical parallelism depends on the torchrun worker cluster",
        }
