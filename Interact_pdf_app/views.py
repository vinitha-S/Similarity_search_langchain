import os
from django.http import JsonResponse
from langchain.chains import RetrievalQA
from langchain.chat_models import ChatOpenAI
from rest_framework.parsers import MultiPartParser, FormParser
from .models import UploadedFile
from .serializers import UploadedFileSerializer
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores.faiss import FAISS
from rest_framework.generics import CreateAPIView
import docsearch  # Import the docsearch library




class UploadedFileCreateAPIView(CreateAPIView):
    serializer_class = UploadedFileSerializer
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        try:
            # Create and validate the serializer
            serializer = UploadedFileSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # Save the uploaded file(s) to the database
            serializer.save()

            # Retrieve data from the validated serializer
            uploaded_files = UploadedFile.objects.filter(id=serializer.data['id'])
            interact = uploaded_files.first()

            # Use interact.file and interact.query as needed
            pdf_files = [interact.file.path]  # Keep it as a list for consistency
            query = interact.query

            # Process each uploaded file
            all_results = {}
            for file_path in pdf_files:
                results_for_file = self.process_uploaded_file(file_path, query)
                all_results.update(results_for_file)

            if not all_results:
                return JsonResponse({"message": "No relevant documents found for the query."}, status=200)

            return JsonResponse({"results": all_results}, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    def process_uploaded_file(self, file_path, query):
        # Load the PDF
        pdf_loader = PyPDFLoader(file_path)
        documents = pdf_loader.load()
        print(len(documents))

        # Use HuggingFace embeddings
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        vector_index = FAISS.load_local("index_store", embeddings)
        retriever = vector_index.as_retriever(search_type="similarity")

        # Incorporate the QA interface and retrieve additional information
        qa_interface = RetrievalQA.from_chain_type(
            llm=ChatOpenAI(model_name='gpt-3.5-turbo-16k'),  # Make sure to define 'llm' appropriately
            chain_type="stuff",
            retriever=retriever,  # Make sure to define 'retriever' appropriately
            return_source_documents=True,
        )
        response = qa_interface(query)
        # Create list to store retrieved documents
        retrieved_docs = []
        res = response['result']
        page_numbers = []  # Add this line to store page numbers

        # Case-insensitive comparison for query matching
        query_lower = query.lower()

        # Iterate through each document and check if it contains the query
        for doc in documents:
            content = doc.page_content.lower()
            if query_lower in content:
                retrieved_docs.append(doc)
                page_numbers.append(doc.metadata['page'])  # Store page numbers

        document_names = {}
        for item in retrieved_docs:
            source_path = item.metadata['source']
            page = item.metadata['page']
            pdf_name = os.path.basename(source_path)

            if pdf_name not in document_names:
                document_names[pdf_name] = []

            document_names[pdf_name].append(page)

        # Debug prints for investigation
        print("Query:", query)
        print("Number of Retrieved Documents:", len(retrieved_docs))
        print("Page Numbers:", page_numbers)  # Print or use page numbers as needed
        document_names['result_key'] = res
        print("Document Names:", document_names)
        return document_names

