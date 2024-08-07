import json
from torch.utils.data import DataLoader, Dataset, RandomSampler
from utils.prompt import get_prompt
import pandas as pd
import os
prompt_type = {
    'qa': '\n\n',
    'qa_evidence': 'Choose the correct answer and explain your reasoning. Your output should be as short as possible\n\n',
    'qa_gene': 'Generate a short document that helps answer the question and choose the correct answer.\n\n',
    'qa_compare': 'Analyze whether each option is rights and choose the best answer.\n\n'
}

class QADataset(Dataset):
    """
    Open-domain generation dataset
    """
    def __init__(self, args):
        self.data = self.read(args.source)
        self.prompts = []
        self.idxs = []
        self.args = args
        self.get_prompted_data()

    def read(self, path):
        qa_data = []
        f = open(path, 'r', encoding='utf-8')
        for line in f.readlines():
            qa_data.append(json.loads(line))
        return qa_data
    
    def get_prompted_data(self):
        for idx in range(len(self.data)):
            if 'info' not in self.data[idx]:
                self.idxs.append(idx)
                self.prompts.append(get_prompt(self.data[idx], self.args))
            

    def __len__(self):
        return len(self.prompts)
    
    def __getitem__(self, index):
        return self.prompts[index]
    
class MCDataset(Dataset):
    """
    Multi-choice dataset
    """
    # generate input for the given subject
    def __init__(self, args, subject):
        self.args = args
        self.subject = subject
        self.data = self.read('test')
        self.idxs = range(len(self.data))
        self.dev_data = self.read('dev') if self.args.n_shot != 0 else []
        self.choices = ['A', 'B', 'C', 'D']
        self.prompts = []
        if args.with_answer == 0:
            self.get_prompted_data()
        else:
            self.get_gt_prompted_data()

    def read(self, mode='test'):
        mmlu_data = pd.read_csv(os.path.join(self.args.source, mode, self.subject + f"_{mode}.csv"), header=None).to_numpy() # no header
        return mmlu_data
    
    def format_subject(self, subject):
        l = subject.split("_")
        s = ""
        for entry in l:
            s += " " + entry
        return s
    
    def format_example(self, data, idx, include_answer=True):
        # Generate one example (idx) for the given data
        prompt = data[idx][0] # question
        k = len(data[idx]) - 2 # count of choices
        for j in range(k):
            prompt += "\n{}. {}".format(self.choices[j], data[idx][j+1]) # append each candidate answer
        prompt += "\nAnswer:"
        if include_answer: # include answer for the few-shot example
            prompt += " {}\n\n".format(data[idx][k + 1])
        return prompt
    
    def gen_prompt(self, k=-1):
        if self.args.task == 'mmlu':
            prompt = "The following are multiple choice questions (with answers) about {}.".format(self.format_subject(self.subject))
        else:
            prompt = "The following are multiple choice questions (with answers)."
        prompt += prompt_type[self.args.type]
        
        if k == -1:
            k = len(self.dev_data)
        for i in range(k):
            prompt += self.format_example(self.dev_data, i)
        return prompt
    
    def get_prompted_data(self):
        base_prompt = self.gen_prompt(self.args.n_shot)
        for idx in range(len(self.data)):
            prompt = self.format_example(self.data, idx, include_answer=False)
            prompt = base_prompt + prompt
            prompt = f"<s>[INST] <<SYS>>\nYou are a helpful assistant<</SYS>> {prompt}[/INST]"
            self.prompts.append(prompt)
        # print(f'total question for {self.subject}: {len(self.prompts)}')

    def get_gt_prompted_data(self):
        base_prompt = self.gen_prompt(self.args.n_shot)
        new_data = []
        for idx in range(len(self.data)):
            prompt = self.format_example(self.data, idx, include_answer=False)
            prompt = base_prompt + prompt
            for ans in ['A', 'B', 'C', 'D']:
                self.prompts.append(prompt + ans)
                new_data.append(self.data[idx])
        self.data = new_data
        self.idxs = range(len(self.data))

    def __len__(self):
        return len(self.prompts)
    
    def __getitem__(self, index):
        return self.prompts[index]



