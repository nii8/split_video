def build_filter_complex(segments):
    """
    Construct a filter_complex string for FFmpeg to trim and concatenate video/audio segments.

    Args:
        segments: List of tuples [(start_sec, end_sec), ...] representing time intervals in seconds

    Returns:
        str: FFmpeg filter_complex string

    Raises:
        ValueError: If segments list is empty
    """
    if not segments:
        raise ValueError("Segments list cannot be empty")

    filters = []
    stream_inputs = []

    for i, (start, end) in enumerate(segments):
        # Video trim and PTS adjustment
        filters.append(f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[v{i}];")
        # Audio trim and PTS adjustment
        filters.append(
            f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{i}];"
        )
        # Add to concat inputs
        stream_inputs.extend([f"[v{i}]", f"[a{i}]"])

    n_segments = len(segments)
    # Concatenate all segments
    concat_filters = (
        f"{''.join(stream_inputs)}concat=n={n_segments}:v=1:a=1[outv][outa]"
    )

    return "".join(filters) + concat_filters
