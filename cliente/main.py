from cnn import CNN  # Importa a classe CNN de um arquivo ou módulo 'cnn'
import torch  # Importa o PyTorch, que é utilizado para criar redes neurais e treinar modelos
from torchvision import datasets  # Importa os datasets da biblioteca torchvision
from torchvision.transforms import v2  # Importa as transformações de imagens da torchvision
import time
from itertools import product
import os
from multiprocessing import Pool, cpu_count
import json
import Pyro5.api
import Client
import concurrent.futures

# Define as transformações que serão aplicadas nas imagens de treino e teste
def define_transforms(height, width):
    data_transforms = {
        'train': v2.Compose([  # Define as transformações para o conjunto de treino
            v2.Resize((height, width)),  # Redimensiona as imagens para as dimensões (height, width)
            v2.Compose([v2.ToImage(), v2.ToDtype(torch.float32, scale=True)]),  # Converte a imagem e define o tipo de dado como float32
            v2.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),  # Normaliza a imagem usando valores de média e desvio padrão para imagens pré-treinadas
        ]),
        'test': v2.Compose([  # Define as transformações para o conjunto de teste
            v2.Resize((height, width)),  # Redimensiona as imagens
            v2.Compose([v2.ToImage(), v2.ToDtype(torch.float32, scale=True)]),  # Converte e define o tipo de dado como float32
            v2.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),  # Normaliza com os mesmos parâmetros
        ])
    }
    return data_transforms  # Retorna as transformações para treino e teste


# Função para carregar as imagens dos diretórios de treino, validação e teste
def read_images(data_transforms):
    train_data = datasets.ImageFolder('./data/resumido/train/', transform=data_transforms['train'])  # Carrega as imagens de treino
    validation_data = datasets.ImageFolder('./data/resumido/validation/', transform=data_transforms['test'])  # Carrega as imagens de validação
    test_data = datasets.ImageFolder('./data/resumido/test/', transform=data_transforms['test'])  # Carrega as imagens de teste
    return train_data, validation_data, test_data  # Retorna os conjuntos de dados


def train_model_parallel(args):
    model_name, num_epochs, learning_rate, weight_decay, replicacoes, train_data, validation_data, test_data = args
    cnn = CNN(train_data, validation_data, test_data, 8)
    inicio = time.time()
    acc_media, rep_max = cnn.create_and_train_cnn(model_name, num_epochs, learning_rate, weight_decay, replicacoes)
    fim = time.time()
    duracao = fim - inicio
    return model_name, num_epochs, learning_rate, weight_decay, acc_media, rep_max, duracao


if __name__ == '__main__':
    inicio_total = time.time()  # Marca o início do programa

    print("Escolha o sistema para execução:")
    print("1. Centralizado e um único processo")
    print("2. Centralizado e multiprocesso")
    print("3. Distribuído e multiprocesso")
    escolha = input("Digite o número correspondente ao sistema desejado: ")

    if escolha == "1":
        inicio_sistema = time.time()  # Início do sistema centralizado único
        print("Sistema Centralizado em Único Processo Escolhido.")
        # Define as dimensões das imagens (224x224) e aplica as transformações
        data_transforms = define_transforms(224, 224)
        
        # Carrega os dados de treino, validação e teste com as transformações aplicadas
        train_data, validation_data, test_data = read_images(data_transforms)
        
        # Cria uma instância do modelo CNN com os dados carregados e o número de classes (8)
        cnn = CNN(train_data, validation_data, test_data, 8)
        
        # Configurações para treinamento do modelo
        replicacoes = 10  # Número de repetições para treinar o modelo
        #model_names = ['alexnet', 'mobilenet_v3_large', 'mobilenet_v3_small', 'resnet18', 'resnet101', 'vgg11', 'vgg19']
        model_names = ['vgg11', 'vgg19', 'mobilenet_v3_large']
        epochs = [1]  # Número de épocas para treinamento
        learning_rates = [0.001, 0.0001, 0.00001]  # Taxas de aprendizado
        weight_decays = [0, 0.0001]  # Decaimento de peso

        # Gera todas as combinações possíveis de parâmetros
        parameter_combinations = product(model_names, epochs, learning_rates, weight_decays)

        #Define a String responsável por registrar os logs dos treinamentos
        treinametos_str = ""
        # Itera sobre cada combinação de parâmetros
        for model_name, num_epochs, learning_rate, weight_decay in parameter_combinations:
            inicio = time.time()  # Marca o início do tempo de treinamento

            # Treina a CNN utilizando os parâmetros definidos
            acc_media, rep_max = cnn.create_and_train_cnn(model_name, num_epochs, learning_rate, weight_decay, replicacoes)

            fim = time.time()  # Marca o final do tempo de treinamento
            duracao = fim - inicio  # Calcula a duração do treinamento

            # Exibe os resultados do treinamento
            
            resultado = ( 
                
                f"Modelo: {model_name}\n"
                f"Épocas: {num_epochs}\n"
                f"Learning Rate: {learning_rate}\n"
                f"Weight Decay: {weight_decay}\n"
                f"Acurácia Média: {acc_media}\n"
                f"Melhor replicação: {rep_max}\n"
                f"Tempo: {duracao:.2f} segundos\n"
                "---------------------------------\n"
            )
            treinametos_str = treinametos_str+resultado
            
        fim_sistema = time.time()
        treinametos_str = treinametos_str+f"Tempo total para o sistema Centralizado Único Processo: {fim_sistema - inicio_sistema:.2f} segundos\n"
        print(treinametos_str)
    
        
        with open("centralizado_unico_processo.txt", "w") as arquivo:
            arquivo.write(treinametos_str)
    
    elif escolha == "2":
        inicio_sistema = time.time()  # Início do sistema centralizado multiprocesso
        print("Sistema Centralizado em Multiprocesso Escolhido.")

        # Obter número de núcleos disponíveis
        num_nucleos = cpu_count()
        print(f"Usando {num_nucleos} núcleos para treinamento paralelo.")

        # Define as dimensões das imagens (224x224) e aplica as transformações
        data_transforms = define_transforms(224, 224)
        train_data, validation_data, test_data = read_images(data_transforms)

        # Configurações para treinamento do modelo
        replicacoes = 10
        #model_names = ['alexnet', 'mobilenet_v3_large', 'mobilenet_v3_small', 'resnet18', 'resnet101', 'vgg11', 'vgg19']
        model_names = ['vgg11', 'vgg19', 'mobilenet_v3_large']
        epochs = [1]
        learning_rates = [0.001, 0.0001, 0.00001]
        weight_decays = [0, 0.0001]

        parameter_combinations = list(product(model_names, epochs, learning_rates, weight_decays, [replicacoes]))
        args = [(model_name, num_epochs, learning_rate, weight_decay, replicacoes, train_data, validation_data, test_data)
                for model_name, num_epochs, learning_rate, weight_decay, replicacoes in parameter_combinations]

        # Multiprocessamento
        with Pool(processes=num_nucleos) as pool:
            results = pool.map(train_model_parallel, args)
        treinametos_str=""
        for model_name, num_epochs, learning_rate, weight_decay, acc_media, rep_max, duracao in results:
            resultado = ( 
                
                f"Modelo: {model_name}\n"
                f"Épocas: {num_epochs}\n"
                f"Learning Rate: {learning_rate}\n"
                f"Weight Decay: {weight_decay}\n"
                f"Acurácia Média: {acc_media}\n"
                f"Melhor replicação: {rep_max}\n"
                f"Tempo: {duracao:.2f} segundos\n"
                "---------------------------------\n"
            )
            treinametos_str = treinametos_str+resultado
        print(treinametos_str)
        fim_sistema = time.time()
        treinametos_str = treinametos_str+f"Tempo total para o sistema Centralizado Multiprocesso: {fim_sistema - inicio_sistema:.2f} segundos"
        
        with open("centralizado_multiplos_processos.txt", "w") as arquivo:
            arquivo.write(treinametos_str)
        print(treinametos_str)

    elif escolha == "3":
        # Acesse o objeto remoto via Proxy usando um gerenciador de contexto
        with Pyro5.api.Proxy("PYRONAME:node.ai_trainer") as ai_trainer:
            try:
                # Chama o método train remotamente
                resultados = ai_trainer.train("alexnet", 1, 0.001, 1, 2)

                # Exibe os resultados recebidos
                print("Resultados do treinamento:", resultados)
                
                # Chama o método train remotamente
                resultados = ai_trainer.train("mobilenet_v3_small", 1, 0.001, 1, 2)

                # Exibe os resultados recebidos
                print("Resultados do treinamento:", resultados)
            except Exception as e:
                print("Erro durante a comunicação com o servidor:", e)

    elif escolha == "4":
        print('Sistema Distribuído e Multiprocesso.');

        # Configurações para treinamento do modelo
        replicacoes = 2
        #model_names = ['alexnet', 'mobilenet_v3_large', 'mobilenet_v3_small', 'resnet18', 'resnet101', 'vgg11', 'vgg19']
        model_names = ['alexnet', 'mobilenet_v3_large']
        epochs = [1]
        learning_rates = [0.001, 0.0001, 0.00001]
        weight_decays = [0, 0.0001]

        parameter_combinations = list(product(model_names, epochs, learning_rates, weight_decays, [replicacoes]))
        tasks = [(model_name, num_epochs, learning_rate, weight_decay, replicacoes)
                for model_name, num_epochs, learning_rate, weight_decay, replicacoes in parameter_combinations]

        # Conectando aos dois nós
        with Pyro5.api.Proxy("PYRONAME:node.ai_trainer1") as trainer1, Pyro5.api.Proxy("PYRONAME:node.ai_trainer2") as trainer2:
            # Obtendo o número de CPUs de cada nó
            cpu1 = trainer1.get_cpu_count()
            cpu2 = trainer2.get_cpu_count()

            # Calculando a proporção de tarefas
            total_cpus = cpu1 + cpu2
            tasks1 = tasks[: int(len(tasks) * (cpu1 / total_cpus))]
            tasks2 = tasks[int(len(tasks) * (cpu1 / total_cpus)):]

            # Adicionando tarefas aos nós
            trainer1.add_tasks(tasks1)
            trainer2.add_tasks(tasks2)

            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = [
                    executor.submit(trainer1.start_processing()),
                    executor.submit(trainer2.start_processing()),
                ]
                print('aguardando finalizar')
                # Aguarda ambas as tarefas terminarem
                for future in concurrent.futures.as_completed(futures):
                    print("Tarefa finalizada:", future.result())
            
    
    # elif escolha == "4" :      
    #     print("Sistema Distribuído e Multiprocesso Escolhido.")

    #     with Pyro5.api.Proxy("PYRONAME:node.ai_trainer") as ai_trainer:
    #         # Instancia o cliente
    #         client = Client.Client()
    #         try:
    #             # Inicia o pool de threads no servidor com o cliente
    #             ai_trainer.initPool(Pyro5.api.Proxy(client))
    #         except Exception as e:
    #             print(f"Erro durante a execução do sistema distribuído: {e}")
   
    #     fim_total = time.time()
    #     print(f"Tempo total de execução do programa: {fim_total - inicio_total:.2f} segundos")
        
