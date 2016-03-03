from pypeliner.workflow import Workflow

import biowrappers.components.io.vcf.tasks as vcf_tasks
import pypeliner

import tasks

def create_init_reference_dbs_workflow(config):
    
    workflow = Workflow()
    
    if 'cosmic' in config:
        workflow.subworkflow(
            name='cosmic',
            func=create_cosmic_download_workflow,
            args=(
                config['cosmic'],
                pypeliner.managed.OutputFile(config['cosmic']['db_vcf_file']),
            )
        )
    
    if 'dbsnp' in config:
        workflow.subworkflow(
            name='dbsnp',
            func=create_dbsnp_download_workflow,
            args=(
                config['dbsnp'],
                pypeliner.managed.OutputFile(config['dbsnp']['db_vcf_file']),
            )
        )
     
    if 'mappability' in config:
        workflow.subworkflow(
            name='mappability', 
            func=create_download_workflow, 
            args=(
                config['mappability']['url'],
                pypeliner.managed.OutputFile(config['mappability']['mappability_file']),
            )
        )
    
    if 'ref_genome' in config:
        workflow.subworkflow(
            name='ref_genome', 
            func=create_ref_genome_download_and_index_workflow, 
            args=(
                config['ref_genome'],
                pypeliner.managed.OutputFile(config['ref_genome']['fasta_file']),
            )
        )

    return workflow

def create_cosmic_download_workflow(config, out_file):
    
    workflow = Workflow()
    
    workflow.setobj(
        obj=pypeliner.managed.TempOutputObj('remote_path', 'files'),
        value={
            'coding' : config['coding']['remote_path'],
            'non_coding' : config['non_coding']['remote_path']
        },
    )
    
    workflow.transform(
        name='download_files',
        axes=('files',),
        ctx={'local' : True},
        func=tasks.download_from_sftp,
        args=(
            pypeliner.managed.TempOutputFile('download.vcf.gz', 'files'),
            config['host'],
            pypeliner.managed.TempInputObj('remote_path', 'files'),
            config['user_name'],
            config['password']
        )
    )
    
    workflow.transform(
        name='merge',
        axes=(),
        ctx={'mem' : 4},
        func=vcf_tasks.concatenate_vcf_fast,
        args=(
            pypeliner.managed.TempInputFile('download.vcf.gz', 'files'),
            pypeliner.managed.TempOutputFile('merged.vcf'),
        ),
    )
    
    workflow.transform(
        name='sort',
        axes=(),
        ctx={'mem' : 4},
        func=vcf_tasks.sort_vcf,
        args=(
            pypeliner.managed.TempInputFile('merged.vcf'),
            pypeliner.managed.TempOutputFile('sorted.vcf')
        )
    )
    
    workflow.subworkflow(
        name='finalise',
        func=vcf_tasks.finalise_vcf,
        args=(
            pypeliner.managed.TempInputFile('sorted.vcf'),
            pypeliner.managed.OutputFile(out_file)
        ),
    )
        
    return workflow

def create_dbsnp_download_workflow(config, out_file):
    
    workflow = Workflow()
    
    workflow.subworkflow(
        name='download', 
        func=create_download_workflow, 
        args=(
            config['url'], 
            pypeliner.managed.OutputFile(out_file)
        )
    )
        
    workflow.transform(
        name='index',
        ctx={'mem' : 4},
        func=vcf_tasks.index_vcf,
        args=(
            pypeliner.managed.InputFile(out_file),
            pypeliner.managed.OutputFile(out_file + '.tbi')
        )
    )
    
    return workflow

def create_download_workflow(url, file_name):
    
    workflow = Workflow()
        
    workflow.setobj(
        obj=pypeliner.managed.TempOutputObj('url'),
        value=url
    )
    
    workflow.transform(
        name='download',
        ctx={'local' : True},
        func=tasks.download_from_url,
        args=(
            pypeliner.managed.TempInputObj('url'),
            pypeliner.managed.OutputFile(file_name)
        )
    )
    
    return workflow

def create_ref_genome_download_and_index_workflow(config, out_file):
    
    workflow = Workflow()
    
    workflow.subworkflow(
        name='download', 
        func=create_download_workflow, 
        args=(
            config['url'], 
            pypeliner.managed.OutputFile(out_file)
        )
    )
    
    workflow.commandline(
        name='build_dict',
        ctx={'mem' : 6, 'num_retry' : 3, 'mem_retry_increment' : 2},
        args=(
            'samtools',
            'dict',
            pypeliner.managed.InputFile(out_file)
        )
    )
    
    workflow.commandline(
        name='build_fai',
        ctx={'mem' : 6, 'num_retry' : 3, 'mem_retry_increment' : 2},
        args=(
            'samtools',
            'faidx',
            pypeliner.managed.InputFile(out_file)
        )
    )
    
    workflow.commandline(
        name='build_bwa_index', 
        ctx={'mem' : 6, 'num_retry' : 3, 'mem_retry_increment' : 2},
        args=(
            'bwa',
            'index',
            pypeliner.managed.InputFile(out_file)
        )
    )
    
    return workflow