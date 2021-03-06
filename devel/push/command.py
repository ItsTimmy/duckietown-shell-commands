import argparse
import os
import subprocess

from dt_shell import DTCommandAbs, dtslogger
from devel.build import ARCH_MAP

DEFAULT_ARCH = "arm32v7"
DEFAULT_MACHINE = "unix:///var/run/docker.sock"

from dt_shell import DTShell


class DTCommand(DTCommandAbs):
    help = "Push the images relative to the current project"

    @staticmethod
    def command(shell: DTShell, args):
        # configure arguments
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "-C",
            "--workdir",
            default=None,
            help="Directory containing the project to push",
        )
        parser.add_argument(
            "-a",
            "--arch",
            default=DEFAULT_ARCH,
            help="Target architecture for the image to push",
        )
        parser.add_argument(
            "-H",
            "--machine",
            default=DEFAULT_MACHINE,
            help="Docker socket or hostname from where to push the image",
        )
        parser.add_argument(
            "-f",
            "--force",
            default=False,
            action="store_true",
            help="Whether to force the push when the git index is not clean",
        )
        parser.add_argument('-u','--username',default="duckietown",
                            help="the docker registry username to tag the image with")

        parsed, _ = parser.parse_known_args(args=args)
        # ---
        code_dir = parsed.workdir if parsed.workdir else os.getcwd()
        dtslogger.info("Project workspace: {}".format(code_dir))
        # show info about project
        shell.include.devel.info.command(shell, args)
        # get info about current repo
        repo_info = shell.include.devel.info.get_repo_info(code_dir)
        repo = repo_info["REPOSITORY"]
        branch = repo_info["BRANCH"]
        nmodified = repo_info["INDEX_NUM_MODIFIED"]
        nadded = repo_info["INDEX_NUM_ADDED"]
        # check if the index is clean
        if nmodified + nadded > 0:
            dtslogger.warning("Your index is not clean (some files are not committed).")
            dtslogger.warning(
                "If you know what you are doing, use --force to force the execution of the command."
            )
            if not parsed.force:
                exit(1)
            dtslogger.warning("Forced!")
        # create defaults
        user = parsed.username
        default_tag = "%s/%s:%s" % (user, repo, branch)
        tag = "%s/%s:%s-%s" % (user, repo, branch, parsed.arch)
        _run_cmd(["docker", "-H=%s" % parsed.machine, "push", tag])
        # add all supported images to manifest
        env = {"DOCKER_CLI_EXPERIMENTAL": "enabled"}
        dtslogger.info("Creating manifest {}...".format(default_tag))
        for key in ARCH_MAP:
            t = "%s/%s:%s-%s" % (user, repo, branch, key)
            try:
                dtslogger.info("Adding {} to manifest...".format(t))
                cmd = ["docker", "manifest", "create", default_tag, "--amend", t]
                _run_cmd(cmd, env)
            except subprocess.CalledProcessError:
                dtslogger.warning('Could not find %s on DockerHub. It probably doesn\'t exist, which is okay.'%t)
        try:
            dtslogger.info("Pushing manifest to DockerHub...")
            cmd = ["docker", "manifest", "push", "-p", default_tag]
            _run_cmd(cmd, env)
        except subprocess.CalledProcessError as e:
            dtslogger.warning(e.message)   

    @staticmethod
    def complete(shell, word, line):
        return []


def _run_cmd(cmd, env=None):
    dtslogger.debug("$ %s" % cmd)
    environ = os.environ
    if env:
      environ.update(env)
    subprocess.check_call(cmd, env=environ)
