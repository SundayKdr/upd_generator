import os
import codecs
import json
from os import walk
from bs4 import BeautifulSoup

from OneCParser import OneCParser
from UpdGenerator import UpdGenerator

SOURCE_DIR = "source"
SOURCE_JSON_DIR = "source_json"


def doc_gen(invoice_file_name, doc_type):
    json_file_name = assemble_json_file(invoice_file_name, doc_type)
    json_data = parse_json_file(json_file_name)
    UpdGenerator(json_data, invoice_file_name).generate_doc()


def parse_json_file(file_name) -> dict:
    with open(file_name, 'r', encoding="utf-8") as fd:
        file_data = fd.read()
    return json.loads(file_data)


def fill_up_inn_kpp_external(one_c_data):
    with open("static_data/inn_kpp.json", 'r', encoding="utf-8") as inn_kpp:
        inn_data = json.loads(inn_kpp.read())

        seller = one_c_data["СчФакт"]["Продавец"]
        buyer = one_c_data["СчФакт"]["Покупатель"]

        seller_name = seller["НаимОрг"].lower()
        buyer_name = buyer["НаимОрг"].lower()
        seller_new_data = {}
        buyer_new_data = {}
        for org in inn_data:
            if org.lower() in seller_name:
                seller_new_data = inn_data[org]
                continue
            if org.lower() in buyer_name:
                buyer_new_data = inn_data[org]

        if not seller_new_data or not buyer_new_data:
            print(f"Не найден продавец {seller_name} или покупатель {buyer_name} в файле inn_kpp.json")
            raise Exception()

        seller["ИНН"] = seller_new_data["ИНН"]
        seller["КПП"] = seller_new_data["КПП"]
        buyer["ИНН"] = buyer_new_data["ИНН"]
        buyer["КПП"] = buyer_new_data["КПП"]


def assemble_json_file(one_c_file_name, doc_type):
    invoice_file_name = decode_file_to_utf8(one_c_file_name)
    with open(invoice_file_name, 'r', encoding="utf-8") as invoice_file:
        one_c_data = OneCParser(invoice_file.read(), doc_type).get_data()
    signatory = prepare_signatory(one_c_data["СчФакт"]["Продавец"]["НаимОрг"], "static_data/SignatoryInfo.json")
    edo = prepare_edo_info("static_data/edo_info.xml", buyer_name=one_c_data["СчФакт"]["Покупатель"]["НаимОрг"],
                           seller_name=one_c_data["СчФакт"]["Продавец"]["НаимОрг"])
    json_file_name = os.path.join(os.path.curdir, SOURCE_JSON_DIR,
                                  os.path.basename(one_c_file_name).replace("xml", "json"))

    fill_up_inn_kpp_external(one_c_data)

    with open(json_file_name, 'w', encoding="utf-8") as json_file:
        json.dump(one_c_data | signatory | edo, json_file, indent=4, ensure_ascii=False)
    return json_file_name


def prepare_signatory(orgName, file_name):
    start = orgName.find('"') + 1
    end = orgName.rfind('"')

    name = orgName[start:end]
    with open(file_name, 'r', encoding="utf-8") as fd:
        file_data = fd.read()
        data = json.loads(file_data)
    return data[name]


def prepare_edo_info(file_name, buyer_name, seller_name):
    with open(file_name, 'r', encoding="utf-8") as fd:
        xml_file = fd.read()
    file_data = BeautifulSoup(xml_file, features="xml")
    data = {}
    receiver = file_data.find("Орг", attrs={"Имя": buyer_name})
    senders = file_data.findAll("Чел")
    sender = None
    for org in senders:
        if seller_name.lower() in org["Имя"].lower():
            sender = org.find("Отправитель")
    if receiver is None or sender is None:
        msg = f"Не найден {buyer_name} в файле edo_info.xml"
        print(msg)
        raise Exception(msg)
    sender_provider = sender.find("Провайдер")
    data["ЭДО"] = {
        "ИдОтпр": sender["Ид"],
        "ИдПол": receiver["Ид"],
        "ИННЮЛ": sender_provider["ИННЮЛ"],
        "ИдЭДО": sender_provider["ИдЭДО"],
        "НаимОрг": sender_provider["НаимОрг"],
    }
    return data


def decode_file_to_utf8(filename, rewrite=False):
    try:
        if "utf-8" in codecs.open(filename, 'r', 'utf-8').read():
            return filename
    except:
        print(f"Не получилось изменить кодировку на utf8 в файле {filename}")

    with codecs.open(filename, 'r', 'windows-1251') as fd:
        file_data = fd.read()
    file_data = file_data.replace("windows-1251", "utf-8")
    if rewrite:
        new_file_name = filename
    else:
        new_file_name = filename.replace(os.path.basename(filename), "utf8_" + os.path.basename(filename))
    with codecs.open(new_file_name, 'w', 'utf-8') as fd:
        fd.write(file_data)
    return new_file_name


def make_new_docs(doc_type):
    file_list = []
    for (_, _, filenames) in walk(os.path.join(os.curdir, SOURCE_DIR)):
        file_list.extend(filenames)
        break

    for file in file_list:
        file_name = os.path.join(os.path.curdir, SOURCE_DIR, file)
        decoded_file_name = decode_file_to_utf8(file_name, rewrite=True)
        # try:
        doc_gen(decoded_file_name, doc_type)
        # except:
        #     print(f"Проблема с файлом {decoded_file_name}. Результат для этого файла не сгенерирован!")


if __name__ == '__main__':
    print("Генерация xml для ЭДО из вывода 1C v7\n"
          "Поместите сгенерированные файли из 1С в папку source\n"
          "После генерации можно посмотреть какие данные были экспортированы в удобочитаемом формате в папке "
          "source_json\n"
          "Поддерживаемые типы документов и их значения 0(УПД) 1(Торг) 2(Акт - пока недоступно)\n")
    while 1:
        userInput = input("Введите число соответсвующее типу документа и нажмите Enter: ")
        try:
            docType = int(userInput)
            break
        except ValueError:
            print("Некорректный ввод! Введите число соответсвующее типу документа и нажмите Enter 0:УПД 1:Торг 2:Акт: ")

    make_new_docs(str(docType))
    print("\nГотово! Проверяйте папку result\n")
