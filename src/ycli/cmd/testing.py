from pydantic import BaseModel

from yatb import schema
from ycli.base import app, c
from ycli.client import YATB


class ShortTask(BaseModel):
    task_name: str

    category: str
    description: str

    flag: str

    def get_form(self) -> schema.TaskForm:
        return schema.TaskForm(
            task_name=self.task_name,
            category=self.category,
            scoring=schema.DynamicKKSScoring(),
            description=self.description,
            flag=schema.StaticFlag(flag=self.flag),
        )


tasks_to_create: list[ShortTask] = [
    ShortTask(flag="task1", task_name="Warm-up crypto", category="crypto", description="XOR basics"),
    ShortTask(flag="task2", task_name="Heap fun", category="binary", description="UAF exploitation"),
    ShortTask(flag="task3", task_name="SQLi 101", category="web", description="Classic injection"),
    ShortTask(flag="task4", task_name="Forensic trace", category="forensic", description="PCAP puzzle"),
    ShortTask(flag="task5", task_name="Obscure stego", category="other", description="Audio LSB"),
    ShortTask(flag="task6", task_name="RSA baby", category="crypto", description="e=3 low exponent"),
    ShortTask(flag="task7", task_name="Fmt-str 101", category="binary", description="Leak & write"),
    ShortTask(flag="task8", task_name="XSS everywhere", category="web", description="DOM clobbering"),
    ShortTask(flag="task9", task_name="Memory dump", category="forensic", description="WinDbg basics"),
    ShortTask(
        flag="task10",
        task_name="Regex confusion",
        category="other",
        description="Catastrophic backtracking",
    ),
    ShortTask(flag="task11", task_name="CBC bit-flip", category="crypto", description="Padding oracle"),
    ShortTask(flag="task12", task_name="ROP chain", category="binary", description="ret2libc → system"),
    ShortTask(flag="task13", task_name="Race condition", category="web", description="Flask session fix"),
    ShortTask(flag="task14", task_name="ELF timeline", category="forensic", description="Shell history"),
    ShortTask(flag="task15", task_name="Brainf**k encode", category="other", description="Esoteric encoding"),
    ShortTask(flag="task16", task_name="Elliptic twist", category="crypto", description="Curve math"),
    ShortTask(flag="task17", task_name="Sigreturn-oriented", category="binary", description="SROP primer"),
    ShortTask(flag="task18", task_name="SSRF to RCE", category="web", description="Metadata abuse"),
    ShortTask(flag="task19", task_name="Malware config", category="forensic", description="C2 extractor"),
    ShortTask(flag="task20", task_name="Reverse Polish", category="other", description="Obfuscated calc"),
]


@app.command()
async def testing_tasks():
    async with YATB() as y:
        for task in tasks_to_create:
            new_task = await y.create_task(task.get_form())
            c.log(f"Task created: {new_task = }")
