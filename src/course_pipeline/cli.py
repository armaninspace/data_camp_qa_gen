
from __future__ import annotations

import typer
from rich.console import Console

from course_pipeline.flows.course_question_pipeline import (
    course_question_pipeline_flow,
)

app = typer.Typer(help="Course question pipeline starter CLI.")
console = Console()


@app.command()
def run(
    input: str = typer.Option(..., help="Input directory of scraped courses."),
    output: str = typer.Option(..., help="Output run directory."),
) -> None:
    summaries = course_question_pipeline_flow(input_dir=input, output_dir=output)
    console.print(f"Processed {len(summaries)} course(s).")
    for item in summaries:
        console.print(
            f"- {item['course_id']}: {item['answered_count']} answered, "
            f"{item['rejected_count']} rejected"
        )


if __name__ == "__main__":
    app()
