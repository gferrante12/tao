// Do NOT change. Changes will be lost next time file is generated

#define R__DICTIONARY_FILENAME dItmpdIbdIjunodOihepdOacdOcndIel9_amd64_gcc11dIReleasedIJ25dO7dO1dItaoswdIbuilddIDataModeldIRawEventdIsrcdIRawHeaderDict
#define R__NO_DEPRECATION

/*******************************************************************/
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#define G__DICTIONARY
#include "ROOT/RConfig.hxx"
#include "TClass.h"
#include "TDictAttributeMap.h"
#include "TInterpreter.h"
#include "TROOT.h"
#include "TBuffer.h"
#include "TMemberInspector.h"
#include "TInterpreter.h"
#include "TVirtualMutex.h"
#include "TError.h"

#ifndef G__ROOT
#define G__ROOT
#endif

#include "RtypesImp.h"
#include "TIsAProxy.h"
#include "TFileMergeInfo.h"
#include <algorithm>
#include "TCollectionProxyInfo.h"
/*******************************************************************/

#include "TDataMember.h"

// Header files passed as explicit arguments
#include "/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/RawEvent/Event/RawHeader.h"

// Header files passed via #pragma extra_include

// The generated code does not explicitly qualify STL entities
namespace std {} using namespace std;

namespace ROOT {
   static void *new_TaocLcLRawHeader(void *p = nullptr);
   static void *newArray_TaocLcLRawHeader(Long_t size, void *p);
   static void delete_TaocLcLRawHeader(void *p);
   static void deleteArray_TaocLcLRawHeader(void *p);
   static void destruct_TaocLcLRawHeader(void *p);

   // Function generating the singleton type initializer
   static TGenericClassInfo *GenerateInitInstanceLocal(const ::Tao::RawHeader*)
   {
      ::Tao::RawHeader *ptr = nullptr;
      static ::TVirtualIsAProxy* isa_proxy = new ::TInstrumentedIsAProxy< ::Tao::RawHeader >(nullptr);
      static ::ROOT::TGenericClassInfo 
         instance("Tao::RawHeader", ::Tao::RawHeader::Class_Version(), "Event/RawHeader.h", 19,
                  typeid(::Tao::RawHeader), ::ROOT::Internal::DefineBehavior(ptr, ptr),
                  &::Tao::RawHeader::Dictionary, isa_proxy, 4,
                  sizeof(::Tao::RawHeader) );
      instance.SetNew(&new_TaocLcLRawHeader);
      instance.SetNewArray(&newArray_TaocLcLRawHeader);
      instance.SetDelete(&delete_TaocLcLRawHeader);
      instance.SetDeleteArray(&deleteArray_TaocLcLRawHeader);
      instance.SetDestructor(&destruct_TaocLcLRawHeader);
      return &instance;
   }
   TGenericClassInfo *GenerateInitInstance(const ::Tao::RawHeader*)
   {
      return GenerateInitInstanceLocal(static_cast<::Tao::RawHeader*>(nullptr));
   }
   // Static variable to force the class initialization
   static ::ROOT::TGenericClassInfo *_R__UNIQUE_DICT_(Init) = GenerateInitInstanceLocal(static_cast<const ::Tao::RawHeader*>(nullptr)); R__UseDummy(_R__UNIQUE_DICT_(Init));
} // end of namespace ROOT

namespace Tao {
//______________________________________________________________________________
atomic_TClass_ptr RawHeader::fgIsA(nullptr);  // static to hold class pointer

//______________________________________________________________________________
const char *RawHeader::Class_Name()
{
   return "Tao::RawHeader";
}

//______________________________________________________________________________
const char *RawHeader::ImplFileName()
{
   return ::ROOT::GenerateInitInstanceLocal((const ::Tao::RawHeader*)nullptr)->GetImplFileName();
}

//______________________________________________________________________________
int RawHeader::ImplFileLine()
{
   return ::ROOT::GenerateInitInstanceLocal((const ::Tao::RawHeader*)nullptr)->GetImplFileLine();
}

//______________________________________________________________________________
TClass *RawHeader::Dictionary()
{
   fgIsA = ::ROOT::GenerateInitInstanceLocal((const ::Tao::RawHeader*)nullptr)->GetClass();
   return fgIsA;
}

//______________________________________________________________________________
TClass *RawHeader::Class()
{
   if (!fgIsA.load()) { R__LOCKGUARD(gInterpreterMutex); fgIsA = ::ROOT::GenerateInitInstanceLocal((const ::Tao::RawHeader*)nullptr)->GetClass(); }
   return fgIsA;
}

} // namespace Tao
namespace Tao {
//______________________________________________________________________________
void RawHeader::Streamer(TBuffer &R__b)
{
   // Stream an object of class Tao::RawHeader.

   if (R__b.IsReading()) {
      R__b.ReadClassBuffer(Tao::RawHeader::Class(),this);
   } else {
      R__b.WriteClassBuffer(Tao::RawHeader::Class(),this);
   }
}

} // namespace Tao
namespace ROOT {
   // Wrappers around operator new
   static void *new_TaocLcLRawHeader(void *p) {
      return  p ? new(p) ::Tao::RawHeader : new ::Tao::RawHeader;
   }
   static void *newArray_TaocLcLRawHeader(Long_t nElements, void *p) {
      return p ? new(p) ::Tao::RawHeader[nElements] : new ::Tao::RawHeader[nElements];
   }
   // Wrapper around operator delete
   static void delete_TaocLcLRawHeader(void *p) {
      delete (static_cast<::Tao::RawHeader*>(p));
   }
   static void deleteArray_TaocLcLRawHeader(void *p) {
      delete [] (static_cast<::Tao::RawHeader*>(p));
   }
   static void destruct_TaocLcLRawHeader(void *p) {
      typedef ::Tao::RawHeader current_t;
      (static_cast<current_t*>(p))->~current_t();
   }
} // end of namespace ROOT for class ::Tao::RawHeader

namespace ROOT {
   static TClass *vectorlEpairlEcharmUcOunsignedsPlonggRsPgR_Dictionary();
   static void vectorlEpairlEcharmUcOunsignedsPlonggRsPgR_TClassManip(TClass*);
   static void *new_vectorlEpairlEcharmUcOunsignedsPlonggRsPgR(void *p = nullptr);
   static void *newArray_vectorlEpairlEcharmUcOunsignedsPlonggRsPgR(Long_t size, void *p);
   static void delete_vectorlEpairlEcharmUcOunsignedsPlonggRsPgR(void *p);
   static void deleteArray_vectorlEpairlEcharmUcOunsignedsPlonggRsPgR(void *p);
   static void destruct_vectorlEpairlEcharmUcOunsignedsPlonggRsPgR(void *p);

   // Function generating the singleton type initializer
   static TGenericClassInfo *GenerateInitInstanceLocal(const vector<pair<char*,unsigned long> >*)
   {
      vector<pair<char*,unsigned long> > *ptr = nullptr;
      static ::TVirtualIsAProxy* isa_proxy = new ::TIsAProxy(typeid(vector<pair<char*,unsigned long> >));
      static ::ROOT::TGenericClassInfo 
         instance("vector<pair<char*,unsigned long> >", -2, "vector", 389,
                  typeid(vector<pair<char*,unsigned long> >), ::ROOT::Internal::DefineBehavior(ptr, ptr),
                  &vectorlEpairlEcharmUcOunsignedsPlonggRsPgR_Dictionary, isa_proxy, 0,
                  sizeof(vector<pair<char*,unsigned long> >) );
      instance.SetNew(&new_vectorlEpairlEcharmUcOunsignedsPlonggRsPgR);
      instance.SetNewArray(&newArray_vectorlEpairlEcharmUcOunsignedsPlonggRsPgR);
      instance.SetDelete(&delete_vectorlEpairlEcharmUcOunsignedsPlonggRsPgR);
      instance.SetDeleteArray(&deleteArray_vectorlEpairlEcharmUcOunsignedsPlonggRsPgR);
      instance.SetDestructor(&destruct_vectorlEpairlEcharmUcOunsignedsPlonggRsPgR);
      instance.AdoptCollectionProxyInfo(TCollectionProxyInfo::Generate(TCollectionProxyInfo::Pushback< vector<pair<char*,unsigned long> > >()));

      instance.AdoptAlternate(::ROOT::AddClassAlternate("vector<pair<char*,unsigned long> >","std::vector<std::pair<char*, unsigned long>, std::allocator<std::pair<char*, unsigned long> > >"));
      return &instance;
   }
   // Static variable to force the class initialization
   static ::ROOT::TGenericClassInfo *_R__UNIQUE_DICT_(Init) = GenerateInitInstanceLocal(static_cast<const vector<pair<char*,unsigned long> >*>(nullptr)); R__UseDummy(_R__UNIQUE_DICT_(Init));

   // Dictionary for non-ClassDef classes
   static TClass *vectorlEpairlEcharmUcOunsignedsPlonggRsPgR_Dictionary() {
      TClass* theClass =::ROOT::GenerateInitInstanceLocal(static_cast<const vector<pair<char*,unsigned long> >*>(nullptr))->GetClass();
      vectorlEpairlEcharmUcOunsignedsPlonggRsPgR_TClassManip(theClass);
   return theClass;
   }

   static void vectorlEpairlEcharmUcOunsignedsPlonggRsPgR_TClassManip(TClass* ){
   }

} // end of namespace ROOT

namespace ROOT {
   // Wrappers around operator new
   static void *new_vectorlEpairlEcharmUcOunsignedsPlonggRsPgR(void *p) {
      return  p ? ::new(static_cast<::ROOT::Internal::TOperatorNewHelper*>(p)) vector<pair<char*,unsigned long> > : new vector<pair<char*,unsigned long> >;
   }
   static void *newArray_vectorlEpairlEcharmUcOunsignedsPlonggRsPgR(Long_t nElements, void *p) {
      return p ? ::new(static_cast<::ROOT::Internal::TOperatorNewHelper*>(p)) vector<pair<char*,unsigned long> >[nElements] : new vector<pair<char*,unsigned long> >[nElements];
   }
   // Wrapper around operator delete
   static void delete_vectorlEpairlEcharmUcOunsignedsPlonggRsPgR(void *p) {
      delete (static_cast<vector<pair<char*,unsigned long> >*>(p));
   }
   static void deleteArray_vectorlEpairlEcharmUcOunsignedsPlonggRsPgR(void *p) {
      delete [] (static_cast<vector<pair<char*,unsigned long> >*>(p));
   }
   static void destruct_vectorlEpairlEcharmUcOunsignedsPlonggRsPgR(void *p) {
      typedef vector<pair<char*,unsigned long> > current_t;
      (static_cast<current_t*>(p))->~current_t();
   }
} // end of namespace ROOT for class vector<pair<char*,unsigned long> >

namespace {
  void TriggerDictionaryInitialization_RawHeaderDict_Impl() {
    static const char* headers[] = {
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/RawEvent/Event/RawHeader.h",
nullptr
    };
    static const char* includePaths[] = {
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/build/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/Python/3.11.10/include/python3.11",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/Boost/1.85.0",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/log4cpp/1.1.3/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/ROOT/6.30.08/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/CLHEP/2.4.7.1/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J24.2.0/ExternalLibs/CLHEP/2.4.7.1/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/Geant4/10.04.p02.juno/include/geant4",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/HepMC/2.06.11/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/genie/3.04.02/include/GENIE",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/frontier/2.10.2/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/mysql-connector-c/6.1.9/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/mysql-connector-cpp/1.1.12/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/libyaml/0.2.4/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/libonnxruntime/1.17.3/include/onnxruntime",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/libonnxruntime/1.17.3/include/onnxruntime/core/session",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/nuwro/21.09.2/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/RawEvent",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/RawEvent/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/build/DataModel/RawEvent",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/junosw/InstallArea/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/junosw/InstallArea/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.4.0/ExternalLibs/ROOT/6.30.08/include/",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/build/DataModel/RawEvent/",
nullptr
    };
    static const char* fwdDeclCode = R"DICTFWDDCLS(
#line 1 "RawHeaderDict dictionary forward declarations' payload"
#pragma clang diagnostic ignored "-Wkeyword-compat"
#pragma clang diagnostic ignored "-Wignored-attributes"
#pragma clang diagnostic ignored "-Wreturn-type-c-linkage"
extern int __Cling_AutoLoading_Map;
namespace Tao{class __attribute__((annotate("$clingAutoload$/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/RawEvent/Event/RawHeader.h")))  RawHeader;}
)DICTFWDDCLS";
    static const char* payloadCode = R"DICTPAYLOAD(
#line 1 "RawHeaderDict dictionary payload"


#define _BACKWARD_BACKWARD_WARNING_H
// Inline headers
#include "/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/RawEvent/Event/RawHeader.h"

#undef  _BACKWARD_BACKWARD_WARNING_H
)DICTPAYLOAD";
    static const char* classesHeaders[] = {
"Tao::RawHeader", payloadCode, "@",
nullptr
};
    static bool isInitialized = false;
    if (!isInitialized) {
      TROOT::RegisterModule("RawHeaderDict",
        headers, includePaths, payloadCode, fwdDeclCode,
        TriggerDictionaryInitialization_RawHeaderDict_Impl, {}, classesHeaders, /*hasCxxModule*/false);
      isInitialized = true;
    }
  }
  static struct DictInit {
    DictInit() {
      TriggerDictionaryInitialization_RawHeaderDict_Impl();
    }
  } __TheDictionaryInitializer;
}
void TriggerDictionaryInitialization_RawHeaderDict() {
  TriggerDictionaryInitialization_RawHeaderDict_Impl();
}
