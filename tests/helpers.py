"""Small helpers shared by test modules."""

from novelty.models import Submission


def as_submission(item: dict) -> Submission:
    return Submission(id=item["id"], headline=item["headline"], body=item["body"], recommend=item["recommend"])
