from procwatch.monitor import ProcessSampler


def test_process_sampler_respects_limits() -> None:
    sampler = ProcessSampler()
    cpu_rows, mem_rows = sampler.sample(top_n_cpu=3, top_n_memory=4)
    assert len(cpu_rows) <= 3
    assert len(mem_rows) <= 4


def test_process_sampler_filters_idle_names() -> None:
    sampler = ProcessSampler()
    assert sampler._is_noise_process("System Idle Process") is True
    assert sampler._is_noise_process("Idle") is True
    assert sampler._is_noise_process("Code.exe") is False
