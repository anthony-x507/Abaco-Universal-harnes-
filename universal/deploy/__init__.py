"""Deploy targets. v1 ships a ZIP packager; GitHub is a stub interface."""

from universal.deploy.github import DeployResult, GitHubDeployTarget
from universal.deploy.packager import ZipPackager

__all__ = ["DeployResult", "GitHubDeployTarget", "ZipPackager"]
