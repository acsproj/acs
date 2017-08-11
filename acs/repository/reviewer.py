import os
import io
import shutil
import requests

from github import Github
from dulwich import porcelain
from acscore.counter import Counter
from acscore.analyzer import Analyzer
from unidiff import PatchSet
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError


SETTINGS = {
    'name': 'CheckiePy',
    'url': 'http://checkiepy.com',
    'attempt': 3,
    'multiplier': 2,
    'max': 10,
}


class Logger:
    def info(self, text):
        print(text)


class Requester:
    def __init__(self, access_token):
        self.github = Github(access_token)

    @retry(stop=stop_after_attempt(SETTINGS['attempt']),
           wait=wait_exponential(multiplier=SETTINGS['multiplier'], max=SETTINGS['max']))
    def get_repositories(self, username):
        return self.github.get_user(username).get_repos()

    @retry(stop=stop_after_attempt(SETTINGS['attempt']),
           wait=wait_exponential(multiplier=SETTINGS['multiplier'], max=SETTINGS['max']))
    def create_pull_request_hook(self, username, repository_name, callback_url):
        self.github.get_user(username).get_repo(repository_name)\
            .create_hook('web', {'url': callback_url, 'content_type': 'json'}, ['pull_request'], True)

    @retry(stop=stop_after_attempt(SETTINGS['attempt']),
           wait=wait_exponential(multiplier=SETTINGS['multiplier'], max=SETTINGS['max']))
    def clone_repository(self, clone_url, save_path, bytes_io):
        if os.path.exists(save_path):
            shutil.rmtree(save_path)
        porcelain.clone(clone_url, save_path, errstream=bytes_io)

    @retry(stop=stop_after_attempt(SETTINGS['attempt']),
           wait=wait_exponential(multiplier=SETTINGS['multiplier'], max=SETTINGS['max']))
    def get_file(self, file_url):
        return requests.get(file_url)

    @retry(stop=stop_after_attempt(SETTINGS['attempt']),
           wait=wait_exponential(multiplier=SETTINGS['multiplier'], max=SETTINGS['max']))
    def get_pull_request(self, username, repository_name, pull_request_number):
        return self.github.get_user(username).get_repo(repository_name).get_pull(pull_request_number)

    @retry(stop=stop_after_attempt(SETTINGS['attempt']),
           wait=wait_exponential(multiplier=SETTINGS['multiplier'], max=SETTINGS['max']))
    def get_latest_commit_from_pull_request(self, pull_request):
        return pull_request.get_commits().reversed[0]

    @retry(stop=stop_after_attempt(SETTINGS['attempt']),
           wait=wait_exponential(multiplier=SETTINGS['multiplier'], max=SETTINGS['max']))
    def create_status(self, commit, state, target_url, description, context):
        commit.create_status(state, target_url, description, context)

    @retry(stop=stop_after_attempt(SETTINGS['attempt']),
           wait=wait_exponential(multiplier=SETTINGS['multiplier'], max=SETTINGS['max']))
    def create_issue_comment(self, pull_request, text):
        pull_request.create_issue_comment(text)

    @retry(stop=stop_after_attempt(SETTINGS['attempt']),
           wait=wait_exponential(multiplier=SETTINGS['multiplier'], max=SETTINGS['max']))
    def create_comment(self, pull_request, text, commit, file, line):
        pull_request.create_comment(text, commit, file, line)


class Reviewer:
    def __init__(self, requester, logger):
        self.requester = requester
        self.logger = logger

    # def run_command(command):
    #     p = Popen(command, stdout=PIPE, stderr=STDOUT)
    #     result = ''
    #     for line in p.stdout.readlines():
    #         result += line.decode() + '\n'
    #     return result

    def get_repositories(self, username):
        self.logger.info("Obtaining of {0}'s repositories was started".format(username))
        repositories = self.requester.get_repositories(username)
        self.logger.info('Repositories was obtained')
        return repositories

    def create_pull_request_hook(self, username, repository_name, callback_url):
        self.logger.info('Setting of pull request web hook was started')
        self.requester.create_pull_request_hook(username, repository_name, callback_url)
        self.logger.info('Pull request web hook was successfully set')

    # def is_need_to_handle_hook(body):
    #     # We need to check repo only if pull request is newly created or received a new commit.
    #     if ACTION in body and (body[ACTION] == OPENED or body[ACTION] == SYNCHRONIZE):
    #         return True
    #     return False

    def clone_repository(self, clone_url, save_path):
        self.logger.info('Repository cloning from {0} to {1} was started'.format(clone_url, save_path))
        if os.path.exists(save_path):
            self.logger.info('Directory {0} already exists. It will be deleted'.format(save_path))
            shutil.rmtree(save_path)
        bytes_io = io.BytesIO()
        self.requester.clone_repository(clone_url, save_path, bytes_io)
        self.logger.info(bytes_io.getvalue().decode())
        self.logger.info('Repository was cloned successfully')

    def get_file(self, file_url, save_path):
        self.logger.info('File downloading from {0} to {1} was started'.format(file_url, save_path))
        file = self.requester.get_file(file_url)
        self.logger.info('File {0} was downloaded successfully'.format(file_url))
        with open(save_path, 'w') as f:
            f.write(file.content.decode())
            self.logger.info('File {0} was saved successfully'.format(save_path))

    #
    # def apply_patch(repo_path):
    #     logger.info('Applying the patch')
    #
    #     # Todo: pass patch filename as argument
    #     message = run_command(["{0}/bash/applypatch.sh".format(settings.BASE_DIR), repo_path])
    #
    #     logger.info(message)
    #
    #
    #
    # def access_to_repo_as_bot(body, bot_name):
    #     repo_name = body[REPOSITORY][NAME]
    #     owner = body[REPOSITORY][OWNER][LOGIN]
    #
    #     logger.info('Trying to get access to {0} repo of {1} with bot {2}'.format(repo_name, owner, bot_name))
    #
    #     github = Github(config.BOT_AUTH)
    #     github_user = github.get_user(owner)
    #     github_repo = github_user.get_repo(repo_name)
    #
    #     logger.info('Access successfully gained')
    #
    #     return github_repo

    def get_pull_request_and_latest_commit(self, username, repository_name, pull_request_number):
        self.logger.info('Obtaining of pull request with number {0} from repository {1}/{2} was started'.format(
            pull_request_number, username, repository_name))
        pull_request = self.requester.get_pull_request(username, repository_name, pull_request_number)
        self.logger.info('Pull request with name {0} was obtained\nObtaining of latest commit was started'
                         .format(pull_request.title))
        commit = self.requester.get_latest_commit_from_pull_request(pull_request)
        self.logger.info('Commit with sha {0} was obtained'.format(commit.sha))
        return pull_request, commit

    def review_pull_request(self, metrics, repository_path, diff_path, pull_request, commit):
        self.logger.info('Review was started')
        self.requester.create_status(commit, 'pending', SETTINGS['url'], 'Review was started', SETTINGS['name'])
        analyzer = Analyzer(metrics)
        counter = Counter()
        with open(os.path.join(repository_path, diff_path), 'r') as f:
            patch_set = PatchSet(f)
        sent_inspection_count = 0
        sent_inspections = {}
        for patch in patch_set:
            file_metrics = counter.metrics_for_file(os.path.join(repository_path, patch.path), verbose=True)
            self.logger.info('Here are metrics for file {0}: {1}'.format(patch.path, file_metrics))
            inspections = analyzer.inspect(file_metrics)
            first_line_in_diff = patch[0][0].diff_line_no
            for hunk in patch:
                self.logger.info('Here are inspections for file {0}: {1}'.format(patch.path, inspections))
                for metric_name, inspection_value in inspections.items():
                    for inspection, value in inspection_value.items():
                        self.logger.info('Inspection {0} has value {1}'.format(inspection, value))
                        if inspection in sent_inspections:
                            continue
                        elif 'lines' not in value:
                            sent_inspections[inspection] = True
                            self.logger.info('Issuing comment {0} for file {1}'.format(value['message'], patch.path))
                            self.requester.create_issue_comment(pull_request, '{0}:\n{1}'.format(patch.path,
                                                                                                 value['message']))
                            sent_inspection_count += 1
                        else:
                            for line in value['lines']:
                                if hunk.target_start <= line <= hunk.target_start + hunk.target_length:
                                    # TODO: What is 3 here?
                                    line_object = hunk[line - hunk.target_start + 3]
                                    target_line = line_object.diff_line_no - first_line_in_diff
                                    self.logger.info('Line with number {0} and value {1} was calculated\n'
                                                     'File {2} was commented on line {3} with message {4}\n'
                                                     'Hunk is from line {5} to line {6}'
                                                     .format(line_object.diff_line_no, line_object.value, patch.path,
                                                             line, value['message'], hunk.target_start,
                                                             hunk.target_start + hunk.target_length))
                                    self.requester.create_comment(pull_request, value['message'], commit, patch.path,
                                                                  target_line)
                                    sent_inspection_count += 1
        if sent_inspection_count == 0:
            self.requester.create_status(commit, 'success', SETTINGS['url'], 'Review was completed. No issues found',
                                         SETTINGS['name'])
        else:
            self.requester.create_status(commit, 'error', SETTINGS['url'], 'Review was completed. Found some issues',
                                         SETTINGS['name'])
        self.logger.info('Review was completed. {0} issues found'.format(sent_inspection_count))

    #
    # @shared_task
    # def handle_hook(json_body, repository_id):
    #
    #     print(logger)
    #
    #     try:
    #         body = json.loads(json_body)
    #
    #         if not is_need_to_handle_hook(body):
    #             return
    #
    #         logger.info('Started review for repo id {0}'.format(repository_id))
    #
    #         repo_path = clone_repo(body)
    #         save_patch(body, repo_path)
    #         apply_patch(repo_path)
    #         save_diff(body, repo_path)
    #
    #         github_repo = access_to_repo_as_bot(body, BOT_NAME)
    #         pull_request, commit = get_pull_request_and_latest_commit(body, github_repo)
    #
    #         # Todo: record mentioned violations
    #         review_repo(repository_id, repo_path, pull_request, commit)
    #
    #         shutil.rmtree(repo_path)
    #
    #         logger.info('Repo {0} review successfully completed'.format(repository_id))
    #     except Exception as e:
    #         logger.exception(e)